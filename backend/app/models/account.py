from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDBase


class AccountStatus(StrEnum):
    active = "active"
    cooldown = "cooldown"
    banned = "banned"


class Account(UUIDBase):
    __tablename__ = "accounts"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    # SECURITY: session JSON only -- password is NEVER stored
    session_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional proxy per account
    proxy_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.active, index=True)

    # Rate limit tracking (source of truth is Redis, this mirrors for UI)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
