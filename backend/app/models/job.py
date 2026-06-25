import uuid
from enum import Enum
from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDBase


class JobMode(str, Enum):
    followers  = "followers"
    following  = "following"
    commenters = "commenters"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused  = "paused"
    done    = "done"
    error   = "error"


class Job(UUIDBase):
    __tablename__ = "jobs"

    profile_username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mode:   Mapped[str] = mapped_column(String(20), default=JobMode.followers)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.pending, index=True)

    # Progress counters
    total_count:   Mapped[int] = mapped_column(Integer, default=0)
    scraped_count: Mapped[int] = mapped_column(Integer, default=0)
    emails_found:  Mapped[int] = mapped_column(Integer, default=0)
    phones_found:  Mapped[int] = mapped_column(Integer, default=0)

    # Celery task reference (for revoke on delete)
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Error details
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    prospects: Mapped[list["Prospect"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan", lazy="dynamic"
    )
