from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_redis: Redis | None = None


def _create_client(url: str) -> Redis:
    # fakeredis:// lets local dev run without a Redis server (dev dependency only)
    if url.startswith(("fakeredis://", "fakeredis+")):
        import fakeredis.asyncio as fakeredis_async

        return fakeredis_async.FakeRedis(decode_responses=True)
    return from_url(url, decode_responses=True)


async def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = _create_client(get_settings().redis_url)
    return _redis


async def get_redis() -> Redis:
    return await get_redis_client()


async def close_redis():
    global _redis
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
