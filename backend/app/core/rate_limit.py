from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.redis import get_redis_client

_KEY = "hotlead:apiratelimit:{ip}:{path}"


async def rate_limit_writes(request: Request) -> None:
    """Fixed-window per-IP limit on pool-exhaustion-prone write endpoints
    (audit AUDIT-2.md H1): POST /jobs and POST /accounts have no throttling
    at all today, so a leaked API key, scripting mistake, or compromised
    frontend can flood job/account creation and mass-trigger cooldowns
    across the whole account pool at once -- worse here than generic API
    abuse, since it directly drives the anti-ban system into a bad state.

    Overridden to a no-op in tests (see conftest.py's `client` fixture) --
    the existing suite creates far more than api_rate_limit_per_minute
    jobs/accounts across its run than any real caller would in a minute, and
    a dedicated test in test_rate_limit_api.py exercises the real dependency
    directly instead.
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = _KEY.format(ip=client_ip, path=request.url.path)

    redis_client = await get_redis_client()
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)

    if count > settings.api_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again in a minute.",
        )
