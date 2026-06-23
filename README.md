<div align="center">

# 🔥 HotLead

**Instagram Audience Scraper & Lead Extractor**

Extract followers, collect public contact data from bios, and export ready-to-use prospect lists for outreach campaigns.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Security](#-security)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Development](#-development)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🎯 Overview

HotLead is a self-hosted web application that extracts public contact data from Instagram follower lists. Given any public Instagram profile, it crawls followers and collects publicly available information (emails, phones, websites) from their bios — producing clean prospect lists for email marketing campaigns.

> **Personal use only.** This tool is designed for self-hosted, internal use. Rate limiting and anti-ban measures are built in to protect your Instagram accounts.

### How it works

```
1. You provide: @profile_handle
       ↓
2. HotLead scrapes followers using the Instagram mobile API
       ↓
3. For each follower: extracts email, phone, website from bio
       ↓
4. You export: CSV or JSON prospect list
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                           │
│                                                                 │
│  ┌──────────────┐    HTTPS    ┌──────────────────────────────┐ │
│  │   Next.js    │ ──────────▶ │         FastAPI              │ │
│  │  (Frontend)  │             │    REST API  /api/v1/        │ │
│  │   :3000      │ ◀────────── │         :8000                │ │
│  └──────────────┘             └──────────┬───────────────────┘ │
│                                          │                      │
│                               ┌──────────▼───────────────────┐ │
│                               │           Redis              │ │
│                               │  Job Queue + Rate Limiter    │ │
│                               │         :6379                │ │
│                               └──────────┬───────────────────┘ │
│                                          │                      │
│                               ┌──────────▼───────────────────┐ │
│                               │      Celery Workers          │ │
│                               │   scrape_followers task      │ │
│                               └──────────┬───────────────────┘ │
│                                          │                      │
│                    ┌─────────────────────┼────────────────────┐ │
│                    │                     │                    │ │
│          ┌─────────▼──────┐   ┌──────────▼─────────┐         │ │
│          │   PostgreSQL   │   │   Account Pool     │         │ │
│          │  Jobs/Prospects│   │  IG Sessions+Proxy │         │ │
│          │     :5432      │   │                    │         │ │
│          └────────────────┘   └──────────┬─────────┘         │ │
│                                          │ instagrapi         │ │
└──────────────────────────────────────────┼────────────────────┘ │
                                           │                       
                              ┌────────────▼──────────────┐       
                              │      Instagram API        │       
                              │  i.instagram.com/api/v1/  │       
                              └───────────────────────────┘       
```

### Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Scraping** | Python 3.12 · [instagrapi](https://github.com/subzeroid/instagrapi) | Simulates Android IG app — most resilient approach in 2026 |
| **API** | FastAPI · async · Pydantic v2 | High performance, auto docs, type safety |
| **Job Queue** | Celery 5 · Redis broker | Pause/resume jobs, multiple workers, retries |
| **Database** | PostgreSQL 16 · SQLAlchemy 2 async · Alembic | ACID, async queries, schema migrations |
| **Cache** | Redis 7 | Job queue + per-account rate limit counters |
| **Frontend** | Next.js 14 App Router · TypeScript · shadcn/ui | Real-time polling, type-safe, accessible UI |
| **Deploy** | Docker Compose · Coolify · Proxmox | Self-hosted on existing homelab infra |

---

## ✨ Features

### Core
- 🔍 **Follower scraping** — extract followers from any public Instagram profile
- 📧 **Contact extraction** — regex-based email, phone, website extraction from bios
- 📊 **Real-time progress** — live job progress via SWR polling
- ⏸ **Pause / Resume** — interrupt and continue any scraping job
- 📤 **Export** — download prospects as CSV or JSON
- 🔄 **Account rotation** — automatically rotates Instagram accounts to avoid rate limits

### Security
- 🔐 **API Key auth** — all endpoints protected by `X-API-Key` header
- 🔒 **Secrets in env only** — zero hardcoded credentials
- 🚫 **Non-root containers** — all Docker services run as unprivileged users
- 🛡 **Input validation** — all inputs validated via Pydantic before processing
- 📝 **Audit trail** — all jobs, accounts, and errors logged with timestamps
- 🔑 **Session-only IG auth** — Instagram passwords never stored; session JSON only

### Rate Limiting & Anti-ban
- ⏱ **Randomized delays** — 1–3s between every Instagram API request
- 📊 **Per-account counters** — max 200 requests/hour tracked in Redis
- 🔄 **Auto-cooldown** — accounts automatically paused on challenge/rate limit
- 🔁 **Smart retry** — Celery retries with exponential backoff on failures

---

## 🔒 Security

HotLead is built **security by design**. Every layer has explicit security controls.

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized API access | API Key required on every request (`X-API-Key` header) |
| Secret leakage | All secrets via env vars; `.env` in `.gitignore`; no defaults in code |
| Privilege escalation | Containers run as non-root (`appuser` / `nextjs`) |
| SQL injection | SQLAlchemy ORM with parameterized queries — no raw SQL |
| Instagram account ban | Session JSON (not password) + delays + rotation + cooldown |
| Data exposure | No personal data stored beyond what's publicly visible on Instagram |
| Container escape | Read-only filesystems where possible; minimal base images |
| Dependency vulnerabilities | Pinned versions in `requirements.txt` + `package-lock.json` |

### Security Checklist

- [ ] Generate strong `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Generate strong `API_KEY`: `openssl rand -hex 32`
- [ ] Never commit `.env` (it's in `.gitignore`)
- [ ] Run `docker compose` behind a reverse proxy (Nginx/Traefik) with TLS
- [ ] Restrict network access — expose only ports 80/443 to internet
- [ ] Rotate Instagram session JSON regularly
- [ ] Enable Coolify's built-in HTTPS before exposing to internet

### Environment Secrets

```bash
# Generate secure secrets:
openssl rand -hex 32  # for SECRET_KEY
openssl rand -hex 32  # for API_KEY
```

---

## 📁 Project Structure

```
hotlead/
├── README.md
├── CLAUDE.md                        # AI context & project decisions
├── docker-compose.yml               # Development stack
├── docker-compose.prod.yml          # Production overrides
├── .env.example                     # Environment template (no secrets)
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt             # Pinned dependencies
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/                # Database migrations
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_jobs.py
│   │   ├── test_prospects.py
│   │   └── test_accounts.py
│   └── app/
│       ├── main.py                  # FastAPI app + startup
│       ├── api/
│       │   └── v1/
│       │       ├── __init__.py      # Router registration
│       │       ├── jobs.py          # POST/GET/DELETE /jobs
│       │       ├── prospects.py     # GET /jobs/{id}/prospects + export
│       │       └── accounts.py      # CRUD /accounts
│       ├── core/
│       │   ├── config.py            # pydantic-settings (env vars)
│       │   ├── database.py          # Async SQLAlchemy engine + session
│       │   ├── redis.py             # Redis client
│       │   ├── security.py          # API key validation middleware
│       │   └── deps.py              # FastAPI dependencies
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py              # Base model with id/timestamps
│       │   ├── job.py               # Job model
│       │   ├── prospect.py          # Prospect model
│       │   └── account.py           # Account model
│       ├── schemas/
│       │   ├── job.py               # JobCreate / JobRead / JobUpdate
│       │   ├── prospect.py          # ProspectRead + filters
│       │   └── account.py           # AccountCreate / AccountRead
│       ├── scraper/
│       │   ├── client.py            # instagrapi wrapper (IGClient)
│       │   ├── account_pool.py      # Account rotation logic
│       │   ├── extractor.py         # email/phone/website from bio
│       │   └── parser.py            # UserShort → Prospect
│       └── workers/
│           ├── celery_app.py        # Celery instance + config
│           └── tasks.py             # scrape_followers, scrape_following
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── components.json              # shadcn/ui config
│   ├── app/
│   │   ├── layout.tsx               # Root layout
│   │   ├── page.tsx                 # Dashboard (job list)
│   │   ├── (auth)/
│   │   │   └── login/page.tsx       # API key entry
│   │   ├── jobs/
│   │   │   ├── new/page.tsx         # Create job form
│   │   │   └── [id]/
│   │   │       ├── page.tsx         # Job detail + live progress
│   │   │       └── prospects/
│   │   │           └── page.tsx     # Prospect table + export
│   │   └── accounts/
│   │       └── page.tsx             # Account pool management
│   ├── components/
│   │   ├── ui/                      # shadcn/ui primitives (auto-generated)
│   │   ├── jobs/
│   │   │   ├── JobCard.tsx
│   │   │   ├── JobProgress.tsx
│   │   │   └── CreateJobForm.tsx
│   │   ├── prospects/
│   │   │   ├── ProspectsTable.tsx
│   │   │   └── ExportButton.tsx
│   │   ├── accounts/
│   │   │   ├── AccountCard.tsx
│   │   │   └── AddAccountForm.tsx
│   │   └── shared/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── StatusBadge.tsx
│   ├── hooks/
│   │   ├── use-job.ts               # SWR polling for job status
│   │   ├── use-prospects.ts
│   │   └── use-accounts.ts
│   ├── lib/
│   │   ├── api.ts                   # Typed fetch wrapper
│   │   └── utils.ts                 # cn() + formatters
│   └── types/
│       └── api.ts                   # Types from OpenAPI schema
│
├── .claude/
│   ├── agents/
│   │   ├── backend-dev.md
│   │   ├── scraper-specialist.md
│   │   ├── frontend-dev.md
│   │   └── devops.md
│   ├── commands/
│   │   ├── new-model.md
│   │   ├── new-endpoint.md
│   │   └── add-account.md
│   └── skills/
│       └── ui-ux-pro-max/           # UI/UX Pro Max v2.6.2
│
├── design-system/
│   └── hotlead/
│       ├── MASTER.md
│       └── pages/
│           ├── dashboard.md
│           ├── jobs.md
│           ├── prospects.md
│           └── accounts.md
│
└── docs/
    ├── quick-reference.md
    ├── api.md                       # API documentation
    └── deployment.md                # Production deploy guide
```

---

## 🛠 Prerequisites

- **Docker** 24+ and **Docker Compose** v2
- **Git**
- At least one Instagram account for scraping (throwaway recommended)
- 2GB RAM minimum (4GB recommended)

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/Samurai33/hotlead.git
cd hotlead
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set **all required values**:

```bash
# Generate secure keys:
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "API_KEY=$(openssl rand -hex 32)"
```

### 3. Start

```bash
docker compose up -d
```

### 4. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Add your first Instagram account

```bash
docker compose exec api python scripts/add_account.py <your_ig_username>
# Enter password when prompted (stored as session only, never as plaintext)
```

### 6. Open the dashboard

```
http://localhost:3000
```

Enter your `API_KEY` from `.env` when prompted.

### 7. Start scraping

1. Click **New Job**
2. Enter an Instagram `@handle`
3. Select mode: `followers` or `following`
4. Hit **Start** — watch the progress in real time
5. When done, click **Export CSV**

---

## ⚙️ Configuration

All configuration is via environment variables. **Never hardcode secrets.**

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | Database user | `hotlead` |
| `POSTGRES_PASSWORD` | Database password | *(generate with openssl)* |
| `POSTGRES_DB` | Database name | `hotlead` |
| `DATABASE_URL` | Full async DB URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `SECRET_KEY` | App secret (JWT/signing) | *(generate with openssl)* |
| `API_KEY` | Frontend→Backend auth key | *(generate with openssl)* |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_WORKERS` | `2` | Number of concurrent scraping workers |
| `IG_REQUEST_DELAY_MIN` | `1.0` | Min seconds between IG requests |
| `IG_REQUEST_DELAY_MAX` | `3.0` | Max seconds between IG requests |
| `IG_MAX_REQUESTS_PER_HOUR` | `200` | Max requests per account per hour |
| `IG_COOLDOWN_MINUTES` | `30` | Minutes to pause a challenged account |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `NEXT_PUBLIC_API_URL` | `http://api:8000` | Backend URL (internal docker network) |

### Full `.env.example`

```bash
# ─── PostgreSQL ───────────────────────────────────────
POSTGRES_USER=hotlead
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=hotlead
DATABASE_URL=postgresql+asyncpg://hotlead:CHANGE_ME@postgres:5432/hotlead

# ─── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── Application ──────────────────────────────────────
SECRET_KEY=CHANGE_ME_generate_with_openssl_rand_hex_32
API_KEY=CHANGE_ME_generate_with_openssl_rand_hex_32

# ─── Scraper tuning ───────────────────────────────────
CELERY_WORKERS=2
IG_REQUEST_DELAY_MIN=1.0
IG_REQUEST_DELAY_MAX=3.0
IG_MAX_REQUESTS_PER_HOUR=200
IG_COOLDOWN_MINUTES=30

# ─── Frontend ─────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://api:8000

# ─── Logging ──────────────────────────────────────────
LOG_LEVEL=INFO
```

---

## 📡 API Reference

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

### Authentication

All endpoints require:

```http
X-API-Key: your-api-key
```

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs` | Create scraping job |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/jobs/{id}` | Get job status & progress |
| `POST` | `/api/v1/jobs/{id}/pause` | Pause running job |
| `POST` | `/api/v1/jobs/{id}/resume` | Resume paused job |
| `DELETE` | `/api/v1/jobs/{id}` | Cancel and delete job |

**Create job:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"profile_username": "cozinha4e20", "mode": "followers"}'
```

### Prospects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/jobs/{id}/prospects` | List prospects (filterable) |
| `GET` | `/api/v1/jobs/{id}/export?fmt=csv` | Download CSV |
| `GET` | `/api/v1/jobs/{id}/export?fmt=json` | Download JSON |

**Query parameters for prospects:**
- `has_email=true` — only prospects with emails
- `has_phone=true` — only with phones
- `limit=100` — page size
- `offset=0` — pagination

### Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/accounts` | Add Instagram account |
| `GET` | `/api/v1/accounts` | List accounts + status |
| `DELETE` | `/api/v1/accounts/{id}` | Remove account |

### Health

```bash
GET /health   →  {"status": "ok", "db": "ok", "redis": "ok"}
```

---

## 💻 Development

### Local backend (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start dependencies only
docker compose up -d postgres redis

# Run API
uvicorn app.main:app --reload --port 8000

# Run worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=debug
```

### Local frontend (without Docker)

```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

### Database migrations

```bash
# Create new migration
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### Running tests

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Code quality

```bash
# Backend
ruff check app/       # linting
ruff format app/      # formatting
mypy app/             # type checking

# Frontend
npm run lint          # ESLint
npm run type-check    # tsc --noEmit
```

---

## 🚢 Deployment

### Coolify (recommended for homelab)

1. In Coolify: **New Resource → Docker Compose**
2. Connect GitHub repo `Samurai33/hotlead`
3. Set branch: `main`
4. Add all environment variables from `.env.example` with real values
5. Enable **HTTPS** (Coolify handles Let's Encrypt)
6. Deploy

### Manual Docker Compose

```bash
# Production: use prod overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Check all services healthy
docker compose ps
```

### Network recommendation (homelab)

For Proxmox + MikroTik setup, assign HotLead its own VLAN:

```
VLAN 160 → 192.168.160.0/30
  .1 = MikroTik gateway
  .2 = HotLead VM/container
```

Expose only ports 80/443 via Coolify's reverse proxy. Redis and PostgreSQL stay internal to the Docker network — never exposed to the host.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow the conventions in `CLAUDE.md`
4. Write tests for new functionality
5. Open a Pull Request

### Commit convention

```
feat: add phone number extraction from bio
fix: handle rate limit error on account pool rotation
docs: update API reference for export endpoint
chore: bump instagrapi to 2.x
```

---

## ⚠️ Disclaimer

HotLead accesses publicly visible Instagram data via the Instagram mobile API. Use responsibly:

- Only scrape profiles you have legitimate interest in
- Respect Instagram's Terms of Service
- Do not use for spam, harassment, or mass unsolicited contact
- This tool is intended for personal/internal use only

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
Built with ❤️ for the homelab · Self-hosted · Privacy-first
</div>
