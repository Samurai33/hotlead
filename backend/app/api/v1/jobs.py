import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.job import Job, JobMode, JobStatus
from app.schemas.job import JobCreate, JobRead, JobListRead

router = APIRouter()


def _enqueue_job(job: Job):
    """Dispatch the right Celery task based on job.mode and return the task result."""
    from app.workers.tasks import scrape_followers, scrape_following, scrape_commenters
    if job.mode == JobMode.commenters:
        return scrape_commenters.apply_async(
            args=[str(job.id), job.target_post_url],
            queue="scraping",
        )
    if job.mode == JobMode.following:
        return scrape_following.apply_async(
            args=[str(job.id), job.profile_username],
            queue="scraping",
        )
    return scrape_followers.apply_async(
        args=[str(job.id), job.profile_username],
        queue="scraping",
    )


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    """Create a new scraping job."""
    job = Job(
        profile_username=payload.profile_username.lstrip("@"),
        mode=payload.mode,
        target_post_url=payload.target_post_url,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = _enqueue_job(job)
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

    task = _enqueue_job(job)
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
