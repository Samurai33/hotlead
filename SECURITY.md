# Security Policy

## Security model

HotLead is designed for **self-hosted, single-operator use**. It is not multi-tenant. Production is publicly reachable (Cloudflare Tunnel → Coolify's Traefik → containers — no forwarded router ports; see `docs/deployment.md`), so the real perimeter is **not** network isolation — it's `X-API-Key` (guarantee 1 below) plus TLS at the Cloudflare edge. Tailscale, where used, is for admin/SSH access to the host VM, not for gating application traffic.

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
- Serve the frontend/API over HTTPS only (the Cloudflare edge terminates TLS; Coolify's Traefik sits behind the tunnel).
- Never forward app ports (3000/8000) or the Coolify management UI's port directly at the router — the whole point of the Cloudflare Tunnel topology is zero forwarded ports. Access Coolify's dashboard only through its own authenticated UI over the tunnel or a VPN (Tailscale), never a bare public IP:port.
- Use dedicated Instagram accounts and per-account proxies. Scraping violates Instagram's ToS — account bans are your risk. Only collect publicly available data and comply with local privacy law (LGPD).

## Reporting a vulnerability

Open a **private security advisory** on GitHub (`Security → Advisories → Report a vulnerability`) on `Samurai33/hotlead`. Do not open public issues for vulnerabilities. Expect an initial response within 7 days.

## Supported versions

Only the latest `main` branch is supported.
