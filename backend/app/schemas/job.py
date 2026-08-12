import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.job import JobMode, JobStatus


class JobCreate(BaseModel):
    profile_username: str = Field(max_length=100)
    mode: JobMode = JobMode.followers
    target_post_url: str | None = Field(default=None, max_length=500)
    # Optional cap on how many profiles to scrape (unlimited if omitted).
    # Stored on Job.total_count, which also doubles as the denominator for
    # the frontend progress bar (audit L6 — this used to be dead: nothing
    # set it, so scrapes ran unbounded and progress bars had no real total).
    max_count: int | None = Field(default=None, gt=0)

    @field_validator("profile_username")
    @classmethod
    def strip_at_and_whitespace(cls, v: str) -> str:
        return v.lstrip("@").strip()

    @field_validator("target_post_url")
    @classmethod
    def validate_instagram_post_url(cls, v: str | None) -> str | None:
        if v is None:
            return None

        url = v.strip()
        if not url:
            return None

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        is_instagram_host = hostname == "instagram.com" or hostname.endswith(".instagram.com")
        path_parts = [part for part in parsed.path.split("/") if part]
        is_media_path = len(path_parts) >= 2 and path_parts[0] in {"p", "reel", "tv"}

        if parsed.scheme not in {"http", "https"} or not is_instagram_host or not is_media_path:
            raise ValueError("target_post_url must be an Instagram post, reel, or tv URL")

        return url

    @model_validator(mode="after")
    def commenters_requires_post_url(self) -> "JobCreate":
        if self.mode == JobMode.commenters and not self.target_post_url:
            raise ValueError("target_post_url is required when mode=commenters")
        return self


class JobRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    profile_username: str
    mode: JobMode
    status: JobStatus
    total_count: int
    scraped_count: int
    emails_found: int
    phones_found: int
    target_post_url: str | None
    celery_task_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class JobListRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    profile_username: str
    mode: JobMode
    status: JobStatus
    total_count: int
    scraped_count: int
    emails_found: int
    phones_found: int
    created_at: datetime
