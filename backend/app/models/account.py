from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedText
from app.models.base import UUIDBase


class AccountStatus(StrEnum):
    active = "active"
    cooldown = "cooldown"  # temporary (rate limit / challenge) — auto-reactivates when cooldown_until passes
    session_expired = "session_expired"  # session dead (LoginRequired) — excluded until re-onboarded, NO auto-recovery
    banned = "banned"


class Account(UUIDBase):
    __tablename__ = "accounts"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    # SECURITY: session JSON only -- password is NEVER stored. Encrypted at
    # rest (audit C2): it's a live, working IG credential, same blast radius
    # as a password if a DB dump or backup ever leaks.
    session_json: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    # Required (audit C1): an account with no proxy shares the deployment
    # host's IP with every other proxy-less account, which reads to
    # Instagram as one IP running multiple sessions -- a multi-accounting
    # signal that can cascade a ban across the whole pool instead of
    # isolating it to one account.
    proxy_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Optional instagrapi locale (e.g. "pt_BR", "en_US") matching the proxy's
    # geography. instagrapi's own set_locale() docstring recommends this;
    # nothing enforced it before (audit AUDIT-2.md M5) -- a device whose
    # locale/timezone doesn't match its egress IP's country is itself a
    # detection signal, compounding the multi-accounting risk C1 addresses.
    # NULL = instagrapi's built-in default (en_US), same as before this field
    # existed.
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.active, index=True)

    # Rate limit tracking (source of truth is Redis, this mirrors for UI)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Consecutive ChallengeRequired/FeedbackRequired count. Resets to 0 on any
    # successful scrape; escalates the account to `banned` once it crosses
    # Settings.ig_challenge_streak_limit instead of cycling
    # cooldown -> active -> cooldown forever on an account IG has already
    # flagged (audit AUDIT-2.md H3).
    challenge_streak: Mapped[int] = mapped_column(Integer, default=0)

    # Self-healing checkout lease (audit AUDIT-2.md H4). Set at checkout time
    # and renewed on every real IG request; a crashed worker's account
    # becomes claimable again once this passes instead of sticking to it
    # forever. NULL means not currently leased.
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
