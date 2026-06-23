import uuid
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDBase


class Prospect(UUIDBase):
    __tablename__ = "prospects"
    __table_args__ = (
        # Fast lookup by job + email filter
        Index("ix_prospects_job_email", "job_id", "email"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Instagram identity
    username:  Mapped[str]       = mapped_column(String(150), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ig_pk:     Mapped[str | None] = mapped_column(String(50),  nullable=True)

    # Contact data extracted from public bio
    email:   Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone:   Mapped[str | None] = mapped_column(String(50),  nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Profile metadata
    biography:   Mapped[str | None] = mapped_column(Text,    nullable=True)
    followers:   Mapped[int]        = mapped_column(Integer, default=0)
    following:   Mapped[int]        = mapped_column(Integer, default=0)
    is_business: Mapped[bool]       = mapped_column(Boolean, default=False)
    is_private:  Mapped[bool]       = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool]       = mapped_column(Boolean, default=False)

    # Relationship
    job: Mapped["Job"] = relationship(back_populates="prospects")  # noqa: F821
