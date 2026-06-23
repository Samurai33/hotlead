"""
Account pool — manages rotation of Instagram accounts.
Rate limit state is tracked in Redis for accuracy across workers.
"""
import logging
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.account import Account, AccountStatus
from app.scraper.client import IGClient

logger = logging.getLogger(__name__)
settings = get_settings()

_RATE_LIMIT_KEY = "hotlead:ratelimit:{account_id}"


async def get_available_client(db: AsyncSession, redis: Redis) -> tuple[Account, IGClient]:
    """
    Returns an active account and its initialized IGClient.
    Rotates to the next account if current one is near rate limit.
    Raises RuntimeError if no accounts are available.
    """
    result = await db.execute(
        select(Account)
        .where(Account.status == AccountStatus.active)
        .order_by(Account.last_used_at.nullsfirst())
    )
    accounts = result.scalars().all()

    if not accounts:
        raise RuntimeError("No active Instagram accounts in pool. Add accounts via /api/v1/accounts.")

    for account in accounts:
        count = await _get_request_count(redis, account.id)
        # Leave 20 requests as safety margin
        if count < settings.ig_max_requests_per_hour - 20:
            client = IGClient(
                username=account.username,
                session_json=account.session_json,
                proxy_url=account.proxy_url,
            )
            await _increment_request_count(redis, account.id)
            return account, client

    raise RuntimeError(
        "All accounts have hit rate limits. "
        f"Retry after {settings.ig_max_requests_per_hour} requests/hour window resets."
    )


async def mark_account_cooldown(
    account: Account, db: AsyncSession, redis: Redis
) -> None:
    """Put account in cooldown after challenge or rate limit."""
    account.status = AccountStatus.cooldown
    account.cooldown_until = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ig_cooldown_minutes
    )
    await db.commit()
    logger.warning(
        f"[{account.username}] Placed in cooldown for {settings.ig_cooldown_minutes}min"
    )


async def save_session(account: Account, client: IGClient, db: AsyncSession) -> None:
    """Persist updated session JSON back to DB."""
    account.session_json = client.get_updated_session()
    account.last_used_at = datetime.now(timezone.utc)
    await db.commit()


async def _get_request_count(redis: Redis, account_id) -> int:
    key = _RATE_LIMIT_KEY.format(account_id=account_id)
    val = await redis.get(key)
    return int(val) if val else 0


async def _increment_request_count(redis: Redis, account_id) -> None:
    key = _RATE_LIMIT_KEY.format(account_id=account_id)
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, 3600)  # 1 hour TTL
    await pipe.execute()
