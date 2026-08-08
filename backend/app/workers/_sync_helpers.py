"""
Synchronous DB and Redis helpers for Celery tasks.
Celery workers are sync — this module wraps DB/Redis for use inside tasks.
"""

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import redis as sync_redis
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.scraper.client import IGClient, RateLimitExceeded

logger = logging.getLogger(__name__)
settings = get_settings()

# Sync engine (psycopg2) — separate from FastAPI's async engine (asyncpg)
_SYNC_DB_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_sync_engine = create_engine(
    _SYNC_DB_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSession = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_sync_redis():
    client = sync_redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        client.close()


def get_job(db: Session, job_id: str):
    from app.models.job import Job

    result = db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    return result.scalar_one_or_none()


def update_job_status(
    db: Session,
    job_id: str,
    status: str,
    scraped_delta: int = 0,
    error_message: str | None = None,
) -> None:
    from app.models.job import Job

    vals = {"status": status, "updated_at": datetime.now(UTC)}
    if error_message is not None:
        vals["error_message"] = error_message
    db.execute(update(Job).where(Job.id == uuid.UUID(job_id)).values(**vals))
    if scraped_delta > 0:
        db.execute(
            text("UPDATE jobs SET scraped_count = scraped_count + :d WHERE id = :id"),
            {"d": scraped_delta, "id": str(job_id)},
        )
    db.commit()


def save_prospect_batch(db: Session, job_id: str, batch: list[dict]) -> int:
    from app.models.prospect import Prospect

    prospects = []
    emails = phones = 0
    for data in batch:
        p = Prospect(
            job_id=uuid.UUID(job_id),
            username=data.get("username", ""),
            full_name=data.get("full_name"),
            ig_pk=data.get("ig_pk"),
            email=data.get("email"),
            phone=data.get("phone"),
            website=data.get("website"),
            biography=data.get("biography"),
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            is_business=data.get("is_business", False),
            is_private=data.get("is_private", False),
            is_verified=data.get("is_verified", False),
        )
        prospects.append(p)
        if p.email:
            emails += 1
        if p.phone:
            phones += 1
    db.bulk_save_objects(prospects)
    if emails > 0 or phones > 0:
        db.execute(
            text(
                "UPDATE jobs SET emails_found=emails_found+:e, phones_found=phones_found+:p WHERE id=:id"
            ),
            {"e": emails, "p": phones, "id": str(job_id)},
        )
    db.commit()
    return emails


def reactivate_cooldown_accounts_sync(db: Session) -> None:
    """Flip any cooldown account whose cooldown_until has passed back to active.

    Anti-ban rule 4 stores a timed cooldown on rate-limit/challenge; this is the
    lazy check that lets the pool recover instead of draining to zero (audit H1).
    """
    from app.models.account import Account, AccountStatus

    db.execute(
        update(Account)
        .where(
            Account.status == AccountStatus.cooldown,
            Account.cooldown_until.isnot(None),
            Account.cooldown_until <= datetime.now(UTC),
        )
        .values(status=AccountStatus.active, cooldown_until=None)
    )
    db.commit()


_RATE_KEY = "hotlead:ratelimit:{}"


def _make_request_hook(account_id, db: Session, redis_client, max_req: int):
    """Build the IGClient request_hook for one checkout (audit H2).

    Fires once per real IG API call (see IGClient._delay): increments the
    per-account Redis counter at request granularity — not once per checkout
    — and mirrors it onto Account.requests_today for the UI. Raises
    RateLimitExceeded once the account crosses the cap so a single long job
    can't blow past the hourly limit; the existing except-block in
    workers/tasks.py already cools the account down and retries on this.
    """
    from app.models.account import Account

    key = _RATE_KEY.format(account_id)

    def hook() -> None:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)
        count, _expire_ok = pipe.execute()
        db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(requests_today=Account.requests_today + 1)
        )
        if int(count) >= max_req - 20:
            raise RateLimitExceeded(f"Hourly request cap reached for account {account_id}")

    return hook


def get_account_sync(db: Session, redis_client) -> tuple:
    from app.models.account import Account, AccountStatus

    reactivate_cooldown_accounts_sync(db)

    max_req = settings.ig_max_requests_per_hour
    result = db.execute(
        select(Account)
        .where(Account.status == AccountStatus.active)
        .order_by(Account.last_used_at.nullsfirst())
    )
    accounts = result.scalars().all()
    if not accounts:
        raise RuntimeError("No active Instagram accounts. Add via /api/v1/accounts.")
    for account in accounts:
        count = int(redis_client.get(_RATE_KEY.format(account.id)) or 0)
        if count < max_req - 20:
            client = IGClient(
                username=account.username,
                session_json=account.session_json,
                proxy_url=account.proxy_url,
                request_hook=_make_request_hook(account.id, db, redis_client, max_req),
            )
            return account, client
    raise RuntimeError("All accounts hit rate limits. Retry after 1 hour.")


def mark_account_cooldown_sync(db: Session, redis_client, account) -> None:
    from app.models.account import AccountStatus

    account.status = AccountStatus.cooldown
    account.cooldown_until = datetime.now(UTC) + timedelta(minutes=settings.ig_cooldown_minutes)
    db.commit()
    logger.warning(f"[{account.username}] Cooldown {settings.ig_cooldown_minutes}min")


def mark_account_session_expired_sync(db: Session, account) -> None:
    """Session is dead (LoginRequired) — no timed recovery. Operator must re-onboard."""
    from app.models.account import AccountStatus

    account.status = AccountStatus.session_expired
    account.cooldown_until = None
    db.commit()
    logger.error(f"[{account.username}] Session expired — re-onboard via add_account.py")


def save_session_sync(db: Session, account, client: IGClient) -> None:
    account.session_json = client.get_updated_session()
    account.last_used_at = datetime.now(UTC)
    db.commit()
