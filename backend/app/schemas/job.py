import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.job import JobMode, JobStatus


class JobCreate(BaseModel):
    profile_username: str
    mode: JobMode = JobMode.followers

    @field_validator("profile_username")
    @classmethod
    def strip_at_and_whitespace(cls, v: str) -> str:
        return v.lstrip("@").strip()


class JobRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               uuid.UUID
    profile_username: str
    mode:             str
    status:           str
    total_count:      int
    scraped_count:    int
    emails_found:     int
    phones_found:     int
    celery_task_id:   str | None
    error_message:    str | None
    created_at:       datetime
    updated_at:       datetime


class JobListRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               uuid.UUID
    profile_username: str
    mode:             str
    status:           str
    scraped_count:    int
    emails_found:     int
    phones_found:     int
    created_at:       datetime
