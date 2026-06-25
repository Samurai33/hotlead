from redis.asyncio import Redis, from_url
from app.core.config import get_settings

_redis: Redis | None = None


async def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def get_redis() -> Redis:
    return await get_redis_client()


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
