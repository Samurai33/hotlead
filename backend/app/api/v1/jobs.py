import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job, JobMode, JobStatus
from app.schemas.job import JobCreate, JobListRead, JobRead

router = APIRouter()
scrape_followers = None
scrape_following = None


def _get_scrape_followers_task():
    global scrape_followers
    if scrape_followers is None:
        from app.workers.tasks import scrape_followers as task

        scrape_followers = task
    return scrape_followers


def _get_scrape_following_task():
    global scrape_following
    if scrape_following is None:
        from app.workers.tasks import scrape_following as task

        scrape_following = task
    return scrape_following


def _get_task_for_mode(mode: str):
    """Return the Celery task matching the job mode."""
    if mode == JobMode.following:
        return _get_scrape_following_task()
    return _get_scrape_followers_task()


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    """Create a new scraping job."""
    job = Job(
        profile_username=payload.profile_username.lstrip("@"),
        mode=payload.mode,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue Celery task matching the requested mode.
    task = _get_task_for_mode(job.mode).apply_async(
        args=[str(job.id), job.profile_username],
        queue="scraping",
    )
    job.celery_task_id = task.id
    job.status = JobStatus.pending
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/", response_model=list[JobListRead])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """List all jobs ordered by creation date."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(100)
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get job details and current progress."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/pause", response_model=JobRead)
async def pause_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Pause a running job gracefully."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.running:
        raise HTTPException(status_code=400, detail=f"Cannot pause job with status '{job.status}'")
    job.status = JobStatus.paused
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/resume", response_model=JobRead)
async def resume_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Resume a paused job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.paused:
        raise HTTPException(status_code=400, detail=f"Cannot resume job with status '{job.status}'")

    task = _get_task_for_mode(job.mode).apply_async(
        args=[str(job.id), job.profile_username],
        queue="scraping",
    )
    job.celery_task_id = task.id
    job.status = JobStatus.pending
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel and delete a job and all its prospects."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Revoke Celery task if running
    if job.celery_task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    await db.delete(job)
    await db.commit()
