from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.logging import configure_logging
from app.core.redis import get_redis_client
from app.core.security import require_api_key

settings = get_settings()
configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Alembic-only in production (audit AUDIT-2.md H7): create_all only adds
    # *missing* tables and never alters existing ones, so it used to be
    # silently inert -- but it split schema authority. A fresh environment's
    # tables came from whatever the current models said, not from replaying
    # the audited migration history, so a migration bug could go undetected
    # until it was the only path taken. `alembic upgrade head` is run
    # explicitly as part of every deploy.
    log.info("hotlead.startup", env=settings.environment)
    yield
    await engine.dispose()
    log.info("hotlead.shutdown")


app = FastAPI(
    title="HotLead API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline security headers (audit AUDIT-2.md M11).

    TLS terminates at Cloudflare, which doesn't add HSTS without an
    explicit toggle -- no layer in the chain currently guarantees it
    end-to-end otherwise. The frontend's Next config already sets these;
    the backend didn't.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/health", tags=["ops"])
async def health():
    from sqlalchemy import text

    db_ok = redis_ok = False
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        r = await get_redis_client()
        await r.ping()
        redis_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }


app.include_router(api_v1_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
