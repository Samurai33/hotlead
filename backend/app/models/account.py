from enum import Enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import UUIDBase


class AccountStatus(str, Enum):
    active = "active"
    cooldown = "cooldown"
    banned = "banned"


class Account(UUIDBase):
    __tablename__ = "accounts"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    # SECURITY: session JSON only — password is NEVER stored
    session_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional proxy
    proxy_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.active, index=True)

    # Rate limiting (tracked in Redis, mirrored here for UI)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
