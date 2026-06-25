import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.redis import get_redis_client, close_redis
from app.core.security import require_api_key
from app.api.v1 import router as api_v1_router

settings = get_settings()

# Structured logging
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    )
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("hotlead.startup", env=settings.environment)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await get_redis_client()  # warm up connection
    log.info("hotlead.startup.done")
    yield
    # Shutdown
    await close_redis()
    await engine.dispose()
    log.info("hotlead.shutdown")


app = FastAPI(
    title="HotLead API",
    version="1.0.0",
    description="Instagram scraper and lead extractor",
    # Security: disable interactive docs in production
    docs_url="/docs"   if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS - tighten origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# Health check - no auth (needed for Docker healthcheck)
@app.get("/health", tags=["ops"])
async def health():
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    from app.core.redis import get_redis_client

    db_ok = redis_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        redis = await get_redis_client()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    status = "ok" if db_ok and redis_ok else "degraded"
    return {"status": status, "db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}


# All API routes require X-API-Key
app.include_router(
    api_v1_router,
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
)
