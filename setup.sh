#!/bin/bash
# HotLead — Setup script para Linux/Mac/Git Bash
# Execute: bash setup.sh

cat > .env << 'ENVEOF'
# ── PostgreSQL ──────────────────────────────────────────────────────────
POSTGRES_USER=hotlead
POSTGRES_PASSWORD=91798a77327350340aeb63ab211a46e3
POSTGRES_DB=hotlead
DATABASE_URL=postgresql+asyncpg://hotlead:91798a77327350340aeb63ab211a46e3@postgres:5432/hotlead

# ── Redis ────────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Security ─────────────────────────────────────────────────────────────
SECRET_KEY=50dfc09370622ebcdfc5f60244e83fa69186012ac27d5efa27df9a458507c13a
API_KEY=c35828996ae06e514e0e3e84c3004c15959ac03d474db605357be2998e1c6e0a

# ── CORS ─────────────────────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000"]

# ── Scraper ──────────────────────────────────────────────────────────────
CELERY_WORKERS=2
IG_REQUEST_DELAY_MIN=1.0
IG_REQUEST_DELAY_MAX=3.0
IG_MAX_REQUESTS_PER_HOUR=200
IG_COOLDOWN_MINUTES=30

# ── Frontend ─────────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://api:8000

# ── App ──────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
ENVIRONMENT=development
ENVEOF

echo "✅ .env criado!"
echo ""
echo "API_KEY: c35828996ae06e514e0e3e84c3004c15959ac03d474db605357be2998e1c6e0a"
echo ""
echo "Próximos passos:"
echo "  docker compose up -d"
echo "  docker compose exec api alembic upgrade head"
echo "  open http://localhost:3000"
