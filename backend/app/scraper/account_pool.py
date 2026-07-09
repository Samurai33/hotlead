"""Account pool with Redis rate-limit tracking and rotation."""

import logging
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.account import Account, AccountStatus
from app.scraper.client import IGClient

logger = logging.getLogger(__name__)
settings = get_settings()
_RATE_KEY = "hotlead:ratelimit:{account_id}"


async def reactivate_cooldown_accounts(db: AsyncSession) -> None:
    """Flip any cooldown account whose cooldown_until has passed back to active (audit H1)."""
    await db.execute(
        update(Account)
        .where(
            Account.status == AccountStatus.cooldown,
            Account.cooldown_until.isnot(None),
            Account.cooldown_until <= datetime.now(UTC),
        )
        .values(status=AccountStatus.active, cooldown_until=None)
    )
    await db.commit()


async def get_available_client(db: AsyncSession, redis: Redis) -> tuple[Account, IGClient]:
    """Return (Account, IGClient) for the least-recently-used active account."""
    await reactivate_cooldown_accounts(db)
    result = await db.execute(
        select(Account)
        .where(Account.status == AccountStatus.active)
        .order_by(Account.last_used_at.nullsfirst())
    )
    accounts = result.scalars().all()
    if not accounts:
        raise RuntimeError("No active IG accounts. Add via /api/v1/accounts.")
    for account in accounts:
        count = int(await redis.get(_RATE_KEY.format(account_id=account.id)) or 0)
        if count < settings.ig_max_requests_per_hour - 20:
            client = IGClient(
                username=account.username,
                session_json=account.session_json,
                proxy_url=account.proxy_url,
            )
            pipe = redis.pipeline()
            pipe.incr(_RATE_KEY.format(account_id=account.id))
            pipe.expire(_RATE_KEY.format(account_id=account.id), 3600)
            await pipe.execute()
            return account, client
    raise RuntimeError("All accounts hit rate limits. Retry in 1h.")


async def mark_account_cooldown(account: Account, db: AsyncSession, redis: Redis) -> None:
    account.status = AccountStatus.cooldown
    account.cooldown_until = datetime.now(UTC) + timedelta(minutes=settings.ig_cooldown_minutes)
    await db.commit()
    logger.warning(f"[{account.username}] Cooldown {settings.ig_cooldown_minutes}min")


async def save_session(account: Account, client: IGClient, db: AsyncSession) -> None:
    account.session_json = client.get_updated_session()
    account.last_used_at = datetime.now(UTC)
    await db.commit()
