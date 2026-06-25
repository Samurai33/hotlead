from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import require_api_key

DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisConn = Annotated[Redis, Depends(get_redis)]
APIKey    = Annotated[str, Depends(require_api_key)]
