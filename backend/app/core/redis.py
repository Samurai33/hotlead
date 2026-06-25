from redis.asyncio import Redis, from_url
from app.core.config import get_settings

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_redis() -> Redis:
    return await get_redis_client()


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
