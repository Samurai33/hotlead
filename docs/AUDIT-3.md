# HotLead — Final Production-Readiness Audit (2026-08-15)

Go/no-go pass covering the whole project — backend, scraper/anti-ban, frontend, and
network/Coolify infra — run as four parallel domain reviews, each verifying every
open item from [AUDIT.md](AUDIT.md) and [AUDIT-2.md](AUDIT-2.md) directly against
current code (file:line evidence, not doc/roadmap claims), plus a fresh pass for
anything new. Findings below are re-triaged and deduplicated against HotLead's
actual threat model (self-hosted, single/few operators, publicly reachable via
Cloudflare Tunnel, no untrusted user content rendered).

**Headline result: every code-level finding from AUDIT.md and AUDIT-2.md is
verified fixed, migrated, and covered by a targeted test.** Nothing found in this
pass blocks going live. This pass's own new findings (H1, H2, M1-M3, L1 below) were
also fixed directly — code changes, new/updated tests, full local verification
(build, lint, mypy, `next build`, and the complete backend suite against real
Postgres/Redis in a throwaway Docker pair — 167/167 passing) — **committed (6
commits) and pushed to `main`, CI green, deploy webhook fired, `/health` confirmed
200 in production.** The one network fact needing the operator's direct
confirmation (N1) has since been checked and closed — see below. What remains is
(a) one small consistency gap (M4) left open by choice, and (b) the already-known
Fase 4/5 operational checklist in [PRODUCTION_ROADMAP.md](PRODUCTION_ROADMAP.md),
none of which has a hidden code dependency.

## ✅ Network confirmation closed (N1)

| # | Finding | Resolution |
|---|---------|------------|
| N1 | Whether the Coolify dashboard's management port was reachable directly on the homelab's public IP, outside the Cloudflare Tunnel — a router-level fact code review couldn't settle. | **Operator checked the ISP router's port-forwarding table directly and confirmed: no individual port-forward rules exist.** The table's only entry is a DMZ rule to one internal host, confirmed by the operator to be the MikroTik firewall — not the Coolify VM. This matches the documented architecture exactly: the ISP box (a "Vivo Box") hands all unsolicited inbound traffic to the MikroTik, which is the layer that actually does per-port control, consistent with "zero forwarded app/admin ports" (`docs/deployment.md`, `CLAUDE.md`). Any stale/unrelated forwarding rules that previously existed on the ISP box were removed during this check. No further action needed. |

## ✅ Fixed in this pass

| # | Finding | Fix | Verification |
|---|---------|-----|---------------|
| H1 | **CSP `script-src` needed a per-request nonce without `'unsafe-inline'`.** The uncommitted diff this audit found had traded a nonce-based `script-src` for `'unsafe-inline'`, on the claim that Next's own framework/RSC-hydration `<script>` tags never picked up a matching `nonce=` on this toolchain (Next 16.3, Turbopack `next build`). Reproducing it showed the real bug: the first attempt set the nonce on the outgoing *response* CSP header only. Next reads the nonce off the *incoming request's* `Content-Security-Policy` header (`get-script-nonce-from-header.js`) — a header that only exists if middleware clones and forwards it via `NextResponse.next({ request: { headers } })`. | `frontend/proxy.ts` now generates a fresh nonce per request (`btoa(crypto.randomUUID())`), builds the full CSP there (moved out of `next.config.mjs`, which can't hold a per-request value), and forwards it on both the request and response headers. `frontend/app/layout.tsx` now `await headers()`s once, which is what actually opts every route into dynamic rendering — without it, `/login` and `/jobs/new` stay statically prerendered and their inline scripts are baked in at *build* time with no nonce at all, a second, subtler way the same bug can resurface. Deliberately **kept the explicit `https://static.cloudflareinsights.com` host entry instead of adding `'strict-dynamic'`** (the originally-recommended fix): `strict-dynamic` makes CSP-3-aware browsers ignore host allowlists entirely, which would have silently broken Cloudflare's own beacon script (injected by the edge, never carries our nonce) — a real interaction the original recommendation didn't account for. Plain `nonce + host allowlist` gets the same "no `unsafe-inline`" outcome without that risk. | Rebuilt (`next build`) and started the production server locally; curled `/login` and `/jobs/new` (both with and without the session cookie) and confirmed the nonce in the response's `Content-Security-Policy` header matches the `nonce="..."` attribute on all 13 inline/script tags in the returned HTML, on repeated requests with different nonces each time. `npm run build`, `npx tsc --noEmit`, `npm run lint` all clean (one pre-existing, unrelated warning — see L2). |
| H2 | **Celery retry jitter was real but wasn't backoff.** `_jittered()` added up to +25% random jitter on a *fixed* base countdown (120s/300s) on every attempt — solved the lockstep-thundering-herd problem, but attempt 1, 2, and 3 all drew from the same window instead of growing per retry. | `_jittered(base_seconds, retries)` now multiplies by `2**retries` before applying jitter, so each successive attempt on a given task roughly doubles its wait — matching Celery's own `retry_backoff` growth curve. All three call sites in `_run_scrape` now pass `self.request.retries`. | New test `test_jittered_backs_off_exponentially_per_retry` (asserts the `2**retries` floor/ceiling across 4 retry counts); full backend suite (167 tests) passing against real Postgres/Redis. |
| M1 | **Export filename built from `profile_username` with no charset allowlist**, flowing unescaped into a `Content-Disposition` header. | `JobCreate.strip_at_and_whitespace` now also validates the result against `^[A-Za-z0-9._]+$` (Instagram's real username charset), raising a 422 instead of silently accepting anything Starlette's own CR/LF guard didn't already block. Length stays governed by the existing `Field(max_length=100)` — deliberately not narrowed to Instagram's real 30-char cap, since `test_profile_username_at_max_length_accepted` already established 100 chars as intentional (matching the `String(100)` column, not the real IG limit). | New tests `test_profile_username_rejects_non_instagram_charset` / `..._accepts_dots_and_underscores`; full suite passing. |
| M2 | **`docker-compose.yml`'s `read_only: false` sat under a comment claiming "Security: read-only root filesystem."** | Comment corrected to state the actual posture and what's needed to safely flip it (`PYTHONDONTWRITEBYTECODE=1` first, since `/app` is root-owned and non-root can't write `.pyc` there). Left `read_only: false` as-is rather than flipping it blind — that's a real behavior change to a file Coolify deploys directly from, worth its own deliberate pass with a live container check, not a drive-by edit during a docs/audit pass. | N/A — comment-only change. |
| M3 | **`prospects/page.tsx` was the one page where a backend failure was indistinguishable from "no prospects yet."** | `useSWR` now destructures `error`; a fetch failure renders the same `ErrorState` + retry block used on the dashboard/accounts/job-detail pages instead of falling through to the empty-state row. | `npm run build` / `tsc --noEmit` clean; manually traced the render logic against the existing `DashboardClient.tsx` pattern it now mirrors. |
| L1 | **Pydantic schemas used `model_config = {"from_attributes": True}` dict literals instead of `ConfigDict(...)`**, against CLAUDE.md's own stated convention. | Switched to `ConfigDict(from_attributes=True)` in `schemas/{job,prospect,account}.py`. | `mypy app/` clean (31 files); full suite passing. |

## 🟡 Left open (deliberately, not urgent)

| # | Finding | Where | Why left open |
|---|---------|-------|----------------|
| M4 | Account deletion wasn't migrated to `useActionState`/Server Action like the rest of the mutations (login, job create, pause/resume/delete-job all were). | `frontend/components/accounts/AccountsClient.tsx:23-24,28-43` | Consistency-only, no security or correctness impact — a real refactor (new Server Action, wiring, testing) rather than a contained fix; better done deliberately than folded into this pass. |
| L2 | `frontend/lib/api.ts:30` uses `window.location.href` for the 401 redirect, tripping a lint warning (doesn't fail the build). | `frontend/lib/api.ts:30` | Pre-existing, unrelated to this pass; a full reload post-cookie-clear is arguably the intended behavior. |
| L3 | No uniqueness/format check on `Account.proxy_url` — nothing stops an operator from accidentally pointing two accounts at the same proxy, recreating the IP-sharing problem the mandatory-proxy fix (AUDIT-2 C1) closed. | `backend/app/models/account.py`, `schemas/account.py` | Self-hosted single-operator tool — operational discipline, not worth enforcing in code today. |
| L4 | `docs/runbook.md` and `SECURITY.md` had doc drift from the auth/network migrations (stale `localStorage` reference, stale "behind a private network" framing). | — | **Fixed directly in this pass** (see the note at the end), per this project's own established convention of fixing doc drift inline during an audit (see AUDIT.md's own header note). |

## ✅ Verified good (every AUDIT.md / AUDIT-2.md item, re-checked against current code)

**Backend** — H1 API rate limiting (`core/rate_limit.py`, tested), H3 `AccountStatus.banned` + `challenge_streak` escalation (migration 005, tested), H4 atomic checkout via `FOR UPDATE SKIP LOCKED` + `leased_until` TTL (migration 006, tested against real Postgres locking), H6 the `lazy="dynamic"` relationship is gone entirely (no ORM relationship between `Job`/`Prospect` at all — explicit `select()` everywhere), H7 `create_all` removed, Alembic-only, H8 explicit `worker_process_init` engine disposal (not accidental import-order), M2 proxy credentials scrubbed from `error_message` before persisting (tested), M7 Celery soft/hard task time limits configured, M9 `structlog` adopted consistently (only one stdlib `logging` import left, and it's just for level-name translation), M10 indexes added on `jobs.created_at`/`accounts.created_at`/`prospects.created_at`/`prospects.followers` (migration 007), L1/L2/L5 dead async `account_pool.py` fully removed, L4 secret entropy + Fernet-key validation at startup.

**Scraper/anti-ban** — C1 `proxy_url` now `NOT NULL` end-to-end (model, schema, migration 004, `add_account.py` hard-exits without `--proxy`), C2 `session_json` encrypted at rest (Fernet via `core/crypto.py`, degrades per-row not per-request on key drift), H2(r2) `FeedbackRequired` imported and handled as its own `AccountFlagged` exception distinct from a generic challenge, H3(r2) banned escalation wired to the same `challenge_streak` column as the backend finding above, H5 extraction now handles `[at]`/`(at)`/`[dot]` obfuscation, keycap-emoji digit normalization, and international (not just BR) phone formats — 20/20 tests passing, M5 `set_locale()`/`set_country()` geo-matching wired from the account's own `locale` field (migration 008), M6 jitter present (see H2 above for the backoff nuance). All five CLAUDE.md anti-ban invariants re-verified end-to-end against live code: 1-3s delay before every IG request with no skip path, 180/hr cap enforced via a Redis counter incremented on every real request (not just at checkout), cooldown auto-reactivation, `session_expired` as a distinct no-timed-recovery state, and `cl.login()` never called when a session already exists.

**Frontend** — M1 the full `localStorage`→httpOnly-cookie migration is complete and correctly wired (grepped the production JS bundle — no key leakage), L5 `error.tsx`/`loading.tsx`/`not-found.tsx` present, L6 Server Components now handle initial data fetch on the dashboard/job-detail/accounts/prospects pages (prospects' missing error state fixed as M3 above), L7 `aria-label`/`role="progressbar"` present everywhere audited, L8 `proxy.ts` gates every non-public route server-side on cookie presence, L9 `noUncheckedIndexedAccess` enabled with exhaustive `Record<Status, ...>` typing, L10 `useActionState` adopted for login/job-create/pause/resume/delete-job (account-delete gap left open — see M4), older-audit M6 migrated off deprecated `next lint` to a proper ESLint 9 flat config, older-audit L7 Dockerfile/CI Node version skew resolved (both on 22). No `dangerouslySetInnerHTML` anywhere in the codebase; export downloads stay header-only auth via the same-origin proxy route (no `?api_key=` in any URL); `npm run build`, `tsc --noEmit`, and the full Docker build all pass clean.

**Network/infra** — topology (Cloudflare edge → tunnel → Traefik → containers, zero forwarded app ports) is internally consistent across CLAUDE.md, docs/deployment.md, and the coolify-deploy-doctor skill. `docker-compose.yml` network segmentation is correct (unique Postgres/Redis aliases, `traefik.docker.network` pinned, `expose` not `ports`, Postgres/Redis never bound to the host). CI gates deploy correctly (`workflow_run` + concurrency group, no stacked deploys); `docker-build` job catches Dockerfile-only breaks that the plain build/test jobs would miss. `pip-audit` + `npm audit --audit-level=high` + `mypy` all run in CI. `.env.example` fully matches `Settings` and the documented Coolify env vars 1:1. Redis `requirepass`, pinned Postgres/Redis image digests, `TrustedHostMiddleware` + `ALLOWED_HOSTS`, and baseline security headers (`X-Content-Type-Options`, `X-Frame-Options`, HSTS in production) all confirmed present in `backend/app/main.py`, none regressed.

## Remaining work

Both N1 and this pass's own code fixes are closed. What's left is purely the
already-known Fase 4/5 operational checklist in
[PRODUCTION_ROADMAP.md](PRODUCTION_ROADMAP.md) — none of it has a hidden code
dependency:

1. Install the backup cron on the VM and run one real restore test.
2. Onboard 2+ dedicated Instagram accounts, each with its own residential proxy (no sharing — L3).
3. Run the Fase 5 end-to-end smoke test (create job → pause/resume → export → forced rotation → cascade delete).
4. Review `docker stats` after 24h of real traffic and tune resource limits if needed.
5. M4 (account-delete `useActionState` consistency) as capacity allows — not urgent in isolation.

## Note on this document and what changed

Per this project's own audit convention (see AUDIT.md's header), doc drift found
during this pass was fixed directly rather than just logged: `SECURITY.md`'s
threat-model description, `docs/runbook.md`'s stale `localStorage` troubleshooting
line, and `docs/PRODUCTION_ROADMAP.md`'s Fase 1-4 checkbox/status drift were all
corrected in the same change as this file. No real IP addresses, resource UUIDs,
or tokens appear anywhere in this document, consistent with this being a public
repository.

This pass also *fixed* its own findings (H1, H2, M1-M3, L1) directly rather than
just documenting them — see the table above for what changed and how each was
verified. Touched: `frontend/proxy.ts`, `frontend/next.config.mjs`,
`frontend/app/layout.tsx`, `frontend/app/jobs/[id]/prospects/page.tsx`,
`backend/app/schemas/{job,prospect,account}.py`, `backend/app/workers/tasks.py`,
`backend/tests/test_job_schema.py`, `backend/tests/test_task_resilience.py`,
`docker-compose.yml` (comment only), across 6 logical commits. **Pushed to `main`
and deployed** — CI green, Coolify deploy webhook fired, `/health` confirmed 200
in production the same session.
