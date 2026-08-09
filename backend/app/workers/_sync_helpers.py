"""
Synchronous DB and Redis helpers for Celery tasks.
Celery workers are sync — this module wraps DB/Redis for use inside tasks.
"""

import logging
import re
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


def dispose_sync_engine() -> None:
    """Drop the pool's connections (audit AUDIT-2.md H8).

    Called from celery_app.py's worker_process_init handler, right after a
    Celery worker forks. Today this module is only ever imported lazily
    (inside _run_scrape, after fork), which is the only reason the classic
    prefork connection-sharing bug doesn't already bite -- an accident of
    import order, not a designed guarantee. This makes the fork-safety
    explicit and robust against a future refactor hoisting that import to
    module level: even if _sync_engine ends up created pre-fork, every child
    process discards whatever it inherited and lazily opens its own.
    """
    _sync_engine.dispose()


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


_CREDENTIALS_IN_URL_RE = re.compile(r"://[^/\s@]*@")


def _scrub_credentials(text_: str) -> str:
    """Strip `user:pass@` from any URL-shaped substring (audit AUDIT-2.md M2).

    proxy_url can embed `user:pass@host`; a connection failure's exception
    text commonly includes it verbatim, and error_message is returned as-is
    via GET /jobs/{id}.
    """
    return _CREDENTIALS_IN_URL_RE.sub("://***@", text_)


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
        vals["error_message"] = _scrub_credentials(error_message)
    db.execute(update(Job).where(Job.id == uuid.UUID(job_id)).values(**vals))
    if scraped_delta > 0:
        db.execute(
            text("UPDATE jobs SET scraped_count = scraped_count + :d WHERE id = :id"),
            {"d": scraped_delta, "id": str(job_id)},
        )
    db.commit()


def save_prospect_batch(db: Session, job_id: str, batch: list[dict]) -> dict:
    """Insert prospects, skipping any (job_id, ig_pk) already saved.

    Pause/resume and Celery retries re-walk the last in-flight page (audit
    M1), so the same followers/following can get yielded twice. ON CONFLICT
    DO NOTHING + RETURNING only reports rows that were actually inserted,
    so callers can update scraped_count/emails_found/phones_found off the
    real delta instead of len(batch) — otherwise those counters inflate past
    what's actually in the prospects table on every resume/retry.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.prospect import Prospect

    if not batch:
        return {"inserted": 0, "emails": 0, "phones": 0}

    rows = [
        {
            "job_id": uuid.UUID(job_id),
            "username": data.get("username", ""),
            "full_name": data.get("full_name"),
            "ig_pk": data.get("ig_pk"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "website": data.get("website"),
            "biography": data.get("biography"),
            "followers": data.get("followers", 0),
            "following": data.get("following", 0),
            "is_business": data.get("is_business", False),
            "is_private": data.get("is_private", False),
            "is_verified": data.get("is_verified", False),
        }
        for data in batch
    ]

    stmt = (
        pg_insert(Prospect)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["job_id", "ig_pk"])
        .returning(Prospect.email, Prospect.phone)
    )
    inserted_rows = db.execute(stmt).all()

    emails = sum(1 for r in inserted_rows if r.email)
    phones = sum(1 for r in inserted_rows if r.phone)
    if emails > 0 or phones > 0:
        db.execute(
            text(
                "UPDATE jobs SET emails_found=emails_found+:e, phones_found=phones_found+:p WHERE id=:id"
            ),
            {"e": emails, "p": phones, "id": str(job_id)},
        )
    db.commit()
    return {"inserted": len(inserted_rows), "emails": emails, "phones": phones}


def update_job_cursor(db: Session, job_id: str, cursor: str | None) -> None:
    """Persist the followers/following pagination max_id onto the job.

    Not committed here — piggybacks on the next natural commit (a prospect
    batch save or the end-of-task session save), matching the per-request
    counter pattern in _make_request_hook: frequent enough (one call per
    ~50-item page) that losing an uncommitted update on crash just means
    re-walking one page, not the whole job.
    """
    from app.models.job import Job

    db.execute(update(Job).where(Job.id == uuid.UUID(job_id)).values(scrape_cursor=cursor))


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


def _make_request_hook(
    account_id, db: Session, redis_client, max_req: int, lease_duration: timedelta
):
    """Build the IGClient request_hook for one checkout (audit H2).

    Fires once per real IG API call (see IGClient._delay): increments the
    per-account Redis counter at request granularity — not once per checkout
    — and mirrors it onto Account.requests_today for the UI. Raises
    RateLimitExceeded once the account crosses the cap so a single long job
    can't blow past the hourly limit; the existing except-block in
    workers/tasks.py already cools the account down and retries on this.

    Also renews the checkout lease (audit H4) on every real request, so a
    live job never loses its account mid-run — only a worker that stops
    making requests (crash, kill -9) lets the lease expire. Not committed
    here — same piggyback-on-the-next-natural-commit reasoning as
    update_job_cursor: requests fire far more often than the ~150s-worst-case
    gap between batch commits, which is still trivially inside the
    multi-minute lease window.
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
            .values(
                requests_today=Account.requests_today + 1,
                leased_until=datetime.now(UTC) + lease_duration,
            )
        )
        if int(count) >= max_req - settings.ig_rate_limit_margin:
            raise RateLimitExceeded(f"Hourly request cap reached for account {account_id}")

    return hook


def get_account_sync(db: Session, redis_client) -> tuple:
    """Claim the least-recently-used active account for exclusive use.

    `FOR UPDATE SKIP LOCKED` makes the claim atomic: two workers racing this
    query never walk away with the same row, because a row locked by one
    transaction is invisible to the other's SELECT instead of being read and
    raced on afterward (audit AUDIT-2.md H4 — the old SELECT-then-later-UPDATE
    let concurrent jobs grab the same "idle" account for a job's entire
    duration). `leased_until` extends that protection past the single SELECT:
    it's set here and renewed by the request_hook on every real IG call, so
    the row stays excluded from other checkouts for as long as the job is
    actually alive, and self-frees if the worker crashes without clearing it.

    All candidate rows returned by the query stay locked until this
    transaction commits or rolls back — including ones we look at but don't
    claim (rate-limited) — so every exit path below must commit before
    returning/raising, or those accounts stay locked for other workers until
    the caller's own commit (which can be a whole job later).
    """
    from app.models.account import Account, AccountStatus

    reactivate_cooldown_accounts_sync(db)

    max_req = settings.ig_max_requests_per_hour
    lease_duration = timedelta(minutes=settings.ig_account_lease_minutes)
    now = datetime.now(UTC)

    result = db.execute(
        select(Account)
        .where(
            Account.status == AccountStatus.active,
            (Account.leased_until.is_(None)) | (Account.leased_until <= now),
        )
        .order_by(Account.last_used_at.nullsfirst())
        .with_for_update(skip_locked=True)
    )
    accounts = result.scalars().all()
    if not accounts:
        raise RuntimeError("No active Instagram accounts. Add via /api/v1/accounts.")
    for account in accounts:
        count = int(redis_client.get(_RATE_KEY.format(account.id)) or 0)
        if count < max_req - settings.ig_rate_limit_margin:
            account.leased_until = now + lease_duration
            account.last_used_at = now
            db.commit()
            client = IGClient(
                username=account.username,
                session_json=account.session_json,
                proxy_url=account.proxy_url,
                locale=account.locale,
                request_hook=_make_request_hook(
                    account.id, db, redis_client, max_req, lease_duration
                ),
            )
            return account, client
    db.commit()  # release FOR UPDATE on the rate-limited rows we're not claiming
    raise RuntimeError("All accounts hit rate limits. Retry after 1 hour.")


def mark_account_cooldown_sync(db: Session, redis_client, account) -> None:
    """Plain rate-limit cooldown — expected, routine, does NOT count toward
    the challenge_streak ban escalation (see mark_account_challenged_sync)."""
    from app.models.account import AccountStatus

    account.status = AccountStatus.cooldown
    account.cooldown_until = datetime.now(UTC) + timedelta(minutes=settings.ig_cooldown_minutes)
    db.commit()
    logger.warning(f"[{account.username}] Cooldown {settings.ig_cooldown_minutes}min")


def mark_account_challenged_sync(db: Session, redis_client, account) -> None:
    """Cooldown after a real challenge/flag (AccountChallenged/AccountFlagged),
    tracking a consecutive streak that escalates to a permanent ban once it
    crosses ig_challenge_streak_limit — instead of cycling
    cooldown -> active -> cooldown forever on an account Instagram has
    already flagged (audit AUDIT-2.md H3). Distinct from
    mark_account_cooldown_sync: a plain rate limit is routine and must not
    push an account toward a ban.
    """
    from app.models.account import AccountStatus

    account.challenge_streak += 1
    if account.challenge_streak >= settings.ig_challenge_streak_limit:
        account.status = AccountStatus.banned
        account.cooldown_until = None
        logger.error(
            f"[{account.username}] Banned after {account.challenge_streak} "
            "consecutive challenges/flags"
        )
    else:
        account.status = AccountStatus.cooldown
        account.cooldown_until = datetime.now(UTC) + timedelta(minutes=settings.ig_cooldown_minutes)
        logger.warning(
            f"[{account.username}] Cooldown {settings.ig_cooldown_minutes}min "
            f"(challenge streak {account.challenge_streak}/{settings.ig_challenge_streak_limit})"
        )
    db.commit()


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
    account.challenge_streak = 0
    # Account stays 'active' after a successful run, so leased_until (unlike
    # status) is the only thing keeping it excluded from checkout — clear it
    # now instead of leaving the pool an account short until the lease times
    # out on its own (audit AUDIT-2.md H4).
    account.leased_until = None
    db.commit()
