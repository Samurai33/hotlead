import csv
import io
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.job import Job
from app.models.prospect import Prospect
from app.schemas.prospect import ProspectRead

router = APIRouter()


@router.get("/{job_id}/prospects", response_model=list[ProspectRead])
async def list_prospects(
    job_id: uuid.UUID,
    has_email: bool | None = Query(None),
    has_phone: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List prospects for a job with optional filters."""
    # Verify job exists
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    query = select(Prospect).where(Prospect.job_id == job_id)

    if has_email is True:
        query = query.where(Prospect.email.isnot(None))
    elif has_email is False:
        query = query.where(Prospect.email.is_(None))

    if has_phone is True:
        query = query.where(Prospect.phone.isnot(None))
    elif has_phone is False:
        query = query.where(Prospect.phone.is_(None))

    query = query.order_by(Prospect.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{job_id}/export")
async def export_prospects(
    job_id: uuid.UUID,
    fmt: str = Query("csv", pattern="^(csv|json)$"),
    has_email: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export all prospects as CSV or JSON download."""
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = select(Prospect).where(Prospect.job_id == job_id)
    if has_email is True:
        query = query.where(Prospect.email.isnot(None))
    query = query.order_by(Prospect.followers.desc())

    result = await db.execute(query)
    prospects = result.scalars().all()

    filename = f"hotlead_{job.profile_username}_{job_id}"

    if fmt == "csv":
        return _export_csv(prospects, filename)
    else:
        return _export_json(prospects, filename)


def _export_csv(prospects: list[Prospect], filename: str) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "username",
            "full_name",
            "email",
            "phone",
            "website",
            "biography",
            "followers",
            "following",
            "is_business",
            "is_verified",
        ],
    )
    writer.writeheader()
    for p in prospects:
        writer.writerow(
            {
                "username": p.username,
                "full_name": p.full_name or "",
                "email": p.email or "",
                "phone": p.phone or "",
                "website": p.website or "",
                "biography": (p.biography or "").replace("\n", " "),
                "followers": p.followers,
                "following": p.following,
                "is_business": p.is_business,
                "is_verified": p.is_verified,
            }
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


def _export_json(prospects: list[Prospect], filename: str) -> StreamingResponse:
    data = [
        {
            "username": p.username,
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone,
            "website": p.website,
            "biography": p.biography,
            "followers": p.followers,
            "following": p.following,
            "is_business": p.is_business,
            "is_verified": p.is_verified,
        }
        for p in prospects
    ]
    return StreamingResponse(
        iter([json.dumps(data, ensure_ascii=False, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
    )
