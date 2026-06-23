from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis as AsyncRedis

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import require_api_key

# Typed dependency aliases for cleaner route signatures
DBSession   = Annotated[AsyncSession, Depends(get_db)]
RedisConn   = Annotated[AsyncRedis,   Depends(get_redis)]
APIKey      = Annotated[str,           Depends(require_api_key)]
