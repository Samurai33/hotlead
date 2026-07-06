---
name: coolify-deploy-doctor
description: "Diagnose and fix apps deployed on Coolify behind a Cloudflare Tunnel (cloudflared → Traefik → containers). Use this skill whenever a deployed app is down, unreachable or misbehaving: 502/503/521 errors, timeouts (curl 000), 'site can't be reached', domain not responding, container unhealthy or crash-looping, deploy webhook failing, TLS/certificate handshake errors, mixed-content errors, or when Coolify shows 'Running' but the app doesn't answer. Also use it BEFORE adding a new docker-compose service to Coolify, to apply the known-good compose patterns and avoid the classic traps."
---

# Coolify Deploy Doctor

Runbook for diagnosing apps deployed on Coolify (Docker Compose buildpack) exposed
through a Cloudflare Tunnel. Distilled from real production incidents — every gotcha
in here cost hours once so it never has to again.

## The request path

Every public request traverses this chain. Diagnosis = finding the first broken link,
so always reason about WHICH layer a symptom points to before running anything:

```
Browser
  → Cloudflare edge          (public DNS, TLS terminates here)
    → cloudflared tunnel     (outbound connector container, no port-forward)
      → coolify-proxy :80    (Traefik, on the external `coolify` docker network)
        → app container      (must be attached to the `coolify` network)
          → internal deps    (postgres/redis on a private network)
```

## Golden rules

1. **Read-only first.** Diagnose with `docker ps/inspect/logs/exec + wget/curl` before
   changing anything. Most incidents are misrouting, not broken code.
2. **Never stack deploys.** One deploy at a time. Triggering redeploys while one is
   running causes minutes of 502/503 churn that looks like a new incident and
   pollutes every measurement you take. Queue one fix, wait for it to finish, re-test.
3. **A 401/403 from the app is GOOD news** during routing diagnosis — the request
   reached the application. Only investigate auth after routing is confirmed.
4. **Fix in git, not in the dashboard.** Compose changes (labels, networks, commands)
   belong in `docker-compose.yml` so the next deploy doesn't silently revert them.
5. Network gear (routers/switches) is production for other services: **read-only
   commands only**, never create/modify/remove rules without explicit approval.

## Symptom → layer map

| Symptom | Likely layer | First check |
|---|---|---|
| Cloudflare error page (502/521/530) | tunnel down or ingress misrouted | `docker logs <cloudflared>` |
| Timeout / curl `000`, but a sibling app on the same server works | Traefik → container | Step 3 below (direct-IP test) |
| `503 no available server` | container unhealthy OR not on `coolify` network | Step 1 + 2 |
| Works, then randomly times out after redeploys | missing `traefik.docker.network` label | Step 4 |
| TLS handshake fails on a subdomain | 2-level subdomain (`a.b.domain.tld`) — free Universal SSL only covers 1 level | rename to 1-level (`a-b.domain.tld`) |
| Browser blocks API calls, "Mixed Content" | frontend built with an `http://` public URL | build args / runtime upgrade |
| Container crash-loops right after deploy | app-level: DNS collision, file permissions, bad env | `docker logs --tail 50` |
| Deploy webhook 401 | missing/wrong `Authorization: Bearer <api-token>` | token in CI secrets |
| Deploy webhook 5xx only from CI, 200 from elsewhere | deploy churn in progress, or stale tunnel connector | wait for idle, then re-test; check for duplicate cloudflared containers |

## Layer-by-layer diagnosis (read-only)

Run on the Coolify host as root (`sudo -i`). Coolify container names look like
`<service>-<resource-uuid>-<timestamp>`; filter with the service name + uuid prefix.

**1. Container state + health**
```bash
docker ps --filter "name=<service>" --format '{{.Names}} | {{.Status}}'
docker logs --tail 50 $(docker ps -qf "name=<service>")
```
`(healthy)` + clean logs → the app is fine, look UP the chain.

**2. Network attachment** — the container must list `coolify`:
```bash
docker inspect -f '{{range $n,$c := .NetworkSettings.Networks}}{{$n}}={{$c.IPAddress}} {{end}}' \
  $(docker ps -qf "name=<service>"); echo
```

**3. Traefik → container reachability** (the decisive test for timeouts):
```bash
# through Traefik, as the public request would arrive:
docker exec coolify-proxy wget -qO- --timeout=5 \
  --header "Host: <public-domain>" http://localhost:80/<healthpath>

# bypassing Traefik, straight to the container's coolify-network IP:
APP_IP=$(docker inspect -f '{{(index .NetworkSettings.Networks "coolify").IPAddress}}' \
  $(docker ps -qf "name=<service>"))
docker exec coolify-proxy wget -qO- --timeout=5 http://$APP_IP:<port>/<healthpath>
```
Direct-IP works but Host-header times out → Traefik is routing to the wrong IP
(see gotcha #1) or the router rule/port label is wrong.

**4. Traefik labels on the container**
```bash
docker inspect -f '{{range $k,$v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' \
  $(docker ps -qf "name=<service>") | grep -i traefik
```
Expect: `traefik.enable=true`, a router `rule=Host(...)`, a service
`loadbalancer.server.port=<port>`, and — critically — `traefik.docker.network=coolify`.

**5. Tunnel** — connector logs and ingress config:
```bash
docker ps -a | grep -i cloudflared        # exactly ONE running connector expected
docker logs --tail 30 $(docker ps -qf "name=cloudflared")
docker exec $(docker ps -qf "name=cloudflared") cat /etc/cloudflared/config.yml
```
Ingress must route each public hostname to `http://coolify-proxy:80`. Two running
cloudflared containers with different configs = source-dependent failures (Cloudflare
load-balances across connectors, so some visitors hit the stale one).

**6. Edge / DNS** — from any machine outside:
```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://<public-domain>/<healthpath>
nslookup <public-domain>   # proxied CNAME to the tunnel expected
```

## Known root causes (each verified in production)

1. **Missing `traefik.docker.network=coolify` label.** A container on multiple
   networks lets Traefik pick an *arbitrary* network IP — sometimes one the proxy
   can't reach. Result: intermittent timeouts that "fix themselves" after restarts.
   Pin the label on every service with a public domain.
2. **Service with a domain not attached to the `coolify` network.** Traefik creates
   the router (so you may see redirects) but can't reach the backend → 503/000.
3. **Bare service names collide on the shared `coolify` network.** Another app's
   `postgres`/`redis` resolves first and your app connects to the wrong DB and
   crash-loops. Give deps unique aliases (e.g. `myapp-postgres`) on the *internal*
   network and use those in connection URLs; keep deps OFF the coolify network.
4. **Inherited HTTP healthcheck on non-HTTP containers.** Workers/schedulers built
   from the API image inherit its `HEALTHCHECK` and show `(unhealthy)` forever.
   Set `healthcheck: { disable: true }` on them.
5. **Non-root container writing to CWD.** `/app` is root-owned; anything that writes
   state files (e.g. celery beat schedule/pidfile) must point them at `/tmp`.
6. **Host port collisions.** Coolify itself listens on :8000 (and other apps grab
   ports too). Use `expose:` — never `ports:` — in production compose; put host
   port bindings in a local-only `docker-compose.override.yml`.
7. **`NEXT_PUBLIC_*` is baked at build time.** It must be passed as a Dockerfile
   `ARG` + `ENV` *before* `npm run build`; changing the env var later does nothing.
   If the platform injects an `http://` URL, upgrade it to `https://` at runtime in
   the API client to avoid mixed content.
8. **Coolify's deploy webhook (`/api/v1/deploy?uuid=...`) requires
   `Authorization: Bearer <api-token>`** — an unauthenticated call returns 401.
   Store URL + token as CI secrets; add `curl --retry 5 --retry-all-errors` because
   the endpoint 502s while a deploy is churning.

## Environment specifics

Concrete hostnames, IPs, dashboard URL and resource UUIDs for this infrastructure are
deliberately **not** in this file (public repo). They live in the operator's private
notes/session memory. Ask the user for the target host/service if not already known.
