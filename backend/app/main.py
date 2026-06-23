import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.security import require_api_key
from app.api.v1 import router as api_v1_router

settings = get_settings()

# ─── Structured logging setup ─────────────────────────
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="HotLead API",
    version="1.0.0",
    description="Instagram scraper & lead extractor API",
    # Security: disable docs in production
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # tighten in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ─── Routes ───────────────────────────────────────────


# Health check (no auth required for Docker healthcheck)
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


# All API routes require API key
app.include_router(
    api_v1_router,
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
)
