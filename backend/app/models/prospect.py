import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase


class Prospect(UUIDBase):
    __tablename__ = "prospects"
    __table_args__ = (
        # Fast lookup by job + email filter
        Index("ix_prospects_job_email", "job_id", "email"),
        # A resumed/retried job re-walks its last in-flight page (audit M1),
        # so save_prospect_batch's ON CONFLICT DO NOTHING relies on this
        # constraint existing. It was previously declared only in Alembic
        # migration 003, not here -- meaning Base.metadata.create_all (which
        # builds tables purely from model definitions) silently produced a
        # schema missing it (audit H7's "schema authority split").
        UniqueConstraint("job_id", "ig_pk", name="uq_prospects_job_id_ig_pk"),
        # The prospect export sorts by follower count with nothing to back
        # it (audit AUDIT-2.md M10).
        Index("ix_prospects_followers", "followers"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Instagram identity
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ig_pk: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Contact data extracted from public bio
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Profile metadata
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    following: Mapped[int] = mapped_column(Integer, default=0)
    is_business: Mapped[bool] = mapped_column(Boolean, default=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
