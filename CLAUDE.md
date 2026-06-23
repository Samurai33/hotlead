# CLAUDE.md

HotLead — Instagram audience scraper & lead extractor. Self-hosted, personal use.
Full docs in [README.md](README.md) — read it only when you need detail this file lacks.

## Stack
- **backend/** — FastAPI 0.111 (async), SQLAlchemy 2 + asyncpg, Alembic, Celery + Redis, instagrapi. Python 3.12.
- **frontend/** — Next.js 14 (App Router), React 18, SWR, Tailwind. TypeScript.
- **Infra** — Postgres 16, Redis 7, Docker Compose. Services: `api`, `worker`, `beat`, `frontend`, `postgres`, `redis`.

## Layout
- `backend/app/api/v1/` — routes (accounts, jobs, prospects)
- `backend/app/models/` `schemas/` — SQLAlchemy models / Pydantic schemas
- `backend/app/scraper/` — `client.py` (instagrapi), `account_pool.py` (rotation/anti-ban), `extractor.py` (parse bios → emails/phones/sites)
- `backend/app/workers/` — `celery_app.py`, `tasks.py` (scrape jobs)
- `backend/app/core/` — `config.py`, `database.py`, `security.py`
- `frontend/app/` — pages; `lib/api.ts` — backend client; `hooks/use-job.ts` — SWR polling

## Commands
Run backend cmds inside the container (`docker compose exec api …`) or from `backend/` with deps installed.

```bash
# Stack
docker compose up -d                              # full stack
docker compose up -d postgres redis               # deps only (for local dev)

# Backend (cwd: backend/)
uvicorn app.main:app --reload --port 8000
celery -A app.workers.celery_app worker --loglevel=info
pytest tests/ -v --cov=app                        # tests
ruff check app/ && ruff format app/               # lint + format
mypy app/                                          # type check
alembic revision --autogenerate -m "msg"          # new migration
alembic upgrade head                               # apply

# Frontend (cwd: frontend/)
npm run dev          # :3000
npm run lint
npm run type-check   # tsc --noEmit
```

## Conventions
- Backend is **fully async** — use `async def`, await DB calls; never block the event loop.
- DB schema changes → always create an Alembic migration; never edit tables by hand.
- Scraping goes through `account_pool` for rotation/rate-limiting — don't call `client.py` directly from routes.
- Config via env (Pydantic Settings in `core/config.py`); see [.env.example](.env.example). Never commit secrets.
- Validate before declaring done: `pytest` + `ruff` (backend), `type-check` + `lint` (frontend).

## Notes
- Personal-use tool; respect built-in rate limits / anti-ban — don't weaken them.
- Frontend types can be regenerated from the live API: `npm run generate-types` (needs api on :8000).
