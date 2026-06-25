# HotLead — Project Context

> Read this file at the start of every session before writing any code.

## What is HotLead?
Self-hosted Instagram audience scraper. Given a public profile @handle,
it extracts followers and collects public contact data (email, phone, website)
from each follower's bio — producing clean prospect lists for outreach campaigns.

**Repo:** https://github.com/Samurai33/hotlead

## Stack (do not change without explicit justification)

| Layer | Tech |
|-------|------|
| Scraping | Python 3.12 · instagrapi (simulates Android IG app) |
| API | FastAPI · async · Pydantic v2 |
| Job queue | Celery 5 · Redis broker |
| Database | PostgreSQL 16 · SQLAlchemy 2 async · Alembic |
| Cache | Redis 7 |
| Frontend | Next.js 14 App Router · TypeScript · shadcn/ui · Tailwind |
| Deploy | Docker Compose · Coolify · Proxmox homelab |

## Architecture

```
Next.js (frontend :3000)
    ↓ HTTP + X-API-Key
FastAPI (backend :8000)
    ↓ enqueue
Redis ↔ Celery Workers
          ↓ uses
      Account Pool (IG sessions + proxy)
          ↓ calls via instagrapi
      i.instagram.com/api/v1/
          ↓ saves
      PostgreSQL (jobs, prospects, accounts)
```

## Security by design rules (never bypass)

1. `X-API-Key` required on every route — validated with `secrets.compare_digest`
2. Instagram passwords are NEVER stored — session JSON only
3. `session_json` never returned in any API read response
4. All containers run as non-root user
5. Redis and PostgreSQL not exposed outside Docker network
6. All secrets via env vars only — no hardcoded values

## Anti-ban rules (Instagram scraping)

1. `time.sleep(random.uniform(1.0, 3.0))` before EVERY IG request
2. Max 200 requests/hour per account (stop at 180 for margin)
3. Auto-rotate accounts when rate limit hit
4. `ChallengeRequired` → mark account cooldown 30min
5. Never call `cl.login()` if session_json exists

## Data models

### Job
```
id, profile_username, mode (followers|following|commenters),
status (pending|running|paused|done|error),
total_count, scraped_count, emails_found, phones_found,
celery_task_id, error_message, created_at, updated_at
```

### Prospect
```
id, job_id (FK → jobs), username, full_name, ig_pk,
email, phone, website, biography,
followers, following, is_business, is_private, is_verified,
created_at
```

### Account
```
id, username, session_json (NO password),
proxy_url, status (active|cooldown|banned),
requests_today, last_used_at, cooldown_until,
created_at, updated_at
```

## API endpoints

```
POST   /api/v1/jobs                       create job
GET    /api/v1/jobs                       list jobs
GET    /api/v1/jobs/{id}                  status + progress
POST   /api/v1/jobs/{id}/pause
POST   /api/v1/jobs/{id}/resume
DELETE /api/v1/jobs/{id}

GET    /api/v1/jobs/{id}/prospects        filterable list
GET    /api/v1/jobs/{id}/export?fmt=csv
GET    /api/v1/jobs/{id}/export?fmt=json

POST   /api/v1/accounts                  add IG account
GET    /api/v1/accounts
DELETE /api/v1/accounts/{id}

GET    /health                            healthcheck (no auth)
GET    /docs                              Swagger (dev only)
```

## File structure

```
hotlead/
├── CLAUDE.md                   ← this file
├── .env.example                ← all env vars documented, no secrets
├── docker-compose.yml
├── docker-compose.prod.yml
├── backend/
│   ├── app/
│   │   ├── api/v1/        jobs.py, prospects.py, accounts.py
│   │   ├── core/          config, database, security, deps
│   │   ├── models/        job.py, prospect.py, account.py
│   │   ├── schemas/       pydantic v2
│   │   ├── scraper/       client, account_pool, extractor
│   │   └── workers/       celery_app, tasks
│   ├── alembic/       migrations
│   └── tests/
├── frontend/
│   ├── app/           Next.js App Router
│   ├── components/
│   ├── hooks/
│   └── lib/
├── .claude/
│   ├── agents/        backend-dev, scraper-specialist, frontend-dev, devops
│   ├── commands/      new-model, new-endpoint, add-account
│   └── skills/        ui-ux-pro-max v2.6.2
└── design-system/ hotlead MASTER + page overrides
```

## Decisions log

| Date | Decision | Reason |
|------|----------|--------|
| 2025-06 | instagrapi over Puppeteer | More resilient to detection, lighter, faster |
| 2025-06 | Celery over asyncio tasks | Pause/resume support, multi-worker, retries |
| 2025-06 | PostgreSQL over MongoDB | ACID, async SQLAlchemy, relational data |
| 2025-06 | Deploy on existing Coolify/Proxmox | No new VPS cost, full control |
| 2025-06 | UI/UX Pro Max v2.6.2 | Design system generation for dashboard style |
