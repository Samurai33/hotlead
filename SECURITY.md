# Security Policy

## Security model

HotLead is designed for **self-hosted, single-operator use** behind a private network (Tailscale/VLAN). It is not multi-tenant.

Guarantees enforced by design (see `CLAUDE.md`):

1. Every API route requires `X-API-Key`, validated with `secrets.compare_digest` (timing-safe). Only `/health` is open.
2. Instagram passwords are **never stored** — only the instagrapi `session_json`.
3. `session_json` is never returned by any read endpoint.
4. All containers run as non-root users.
5. PostgreSQL and Redis are only reachable inside the Docker network.
6. All secrets come from environment variables; nothing sensitive is committed.
7. Swagger (`/docs`) is disabled when `ENVIRONMENT=production`.

## Operator responsibilities

- Generate strong secrets: `openssl rand -hex 32` for `SECRET_KEY` and `API_KEY`.
- Serve the frontend/API over HTTPS only (Coolify proxy handles TLS).
- Do not expose ports 8000/3000 directly to the internet; prefer Tailscale or a reverse proxy with TLS.
- Use dedicated Instagram accounts and per-account proxies. Scraping violates Instagram's ToS — account bans are your risk. Only collect publicly available data and comply with local privacy law (LGPD).

## Reporting a vulnerability

Open a **private security advisory** on GitHub (`Security → Advisories → Report a vulnerability`) on `Samurai33/hotlead`. Do not open public issues for vulnerabilities. Expect an initial response within 7 days.

## Supported versions

Only the latest `main` branch is supported.
