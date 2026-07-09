# HotLead — Audit Findings (2026-07)

Triaged backlog from a full read-only audit (backend, frontend, scraper/workers, infra/docs).
Doc drift was fixed directly in README/CLAUDE.md/roadmap. The items below are **code**
findings that need a decision or dedicated work. Ranked by production impact.

## 🔴 High — fix before real scraping volume

| # | Finding | Where | Impact |
|---|---------|-------|--------|
| H1 | **Cooldown accounts are never reactivated.** Nothing reads `cooldown_until` to flip `cooldown → active`; `get_account_sync` only selects `status == active`. No beat task, no lazy check. | `scraper/account_pool.py:45`, `workers/_sync_helpers.py:150`, `workers/tasks.py:88` | The pool monotonically drains to zero. Every rate-limit/challenge permanently removes an account → eventually all jobs fail with "No active Instagram accounts." **Can brick the single-account smoke test.** |
| H2 | **Rate limit counts checkouts, not requests.** Redis `INCR` runs once when an account is handed out, then a job makes thousands of IG requests without touching the counter. `requests_today` never updated. | `_sync_helpers.py:143`, `account_pool.py:38` | Anti-ban rule 2 (180/hr) is not actually enforced; the only throttle is the random delay. |
| H3 | **Expired session mislabeled as challenge.** `IGClient` maps `LoginRequired` → `AccountChallenged` (same bucket as a real challenge) → 30-min cooldown. No `session_expired` state exists. | `scraper/client.py:61,79,104,134`; `models/account.py:10` | An expired session waits out a pointless cooldown, then (if H1 were fixed) re-fails immediately in a loop. Operator gets no "re-onboard this account" signal. |
| H4 | **Export is broken (401).** Client builds the download URL with `?api_key=` query param, but the backend export route is protected only by the router-level `X-API-Key` **header** dep and never reads the query param. `<a download>` sends no header. | `frontend/lib/api.ts:98`, `frontend/app/jobs/[id]/prospects/page.tsx:30`, `backend/app/api/v1/prospects.py:51` | CSV/JSON export fails end-to-end. Fix: read `api_key` query param on the export route (and drop it from other logs), or stream via fetch+blob with the header. |

## 🟠 Medium

| # | Finding | Where | Impact |
|---|---------|-------|--------|
| M1 | **Resume = restart from zero.** `resume_job` dispatches a fresh task with no cursor; retries also restart the iterator. No unique constraint on `(job_id, ig_pk)`. | `api/v1/jobs.py:119`, `workers/tasks.py:86` | Duplicate prospects + inflated `emails_found`/`phones_found` on every pause/resume or retry. Contradicts the "pause/resume" rationale in the decisions log. |
| M2 | **Commenters mode yields empty contacts.** `media_comments` returns `UserShort`; `_normalize_short` hardcodes bio/email/phone/website = None. No per-PK `user_info` hydration. | `scraper/client.py:114,172` | Commenter jobs produce prospects with no contact data — useless for the product goal. Either hydrate or document as identity-only. |
| M3 | **307 header-drop risk on POST.** `POST /api/v1/jobs` & `/accounts` without trailing slash 307-redirect; some clients drop `X-API-Key`/body on the hop. | `api/v1/*.py` (`@router.post("/")`) | External API consumers get confusing 401s. Fix: register routes at `""` or document/alias. (Frontend follows redirects, so UI is unaffected.) |
| M4 | **Login "validation" hits unauthenticated `/health`.** A wrong key is accepted at login and only fails on the first real API call. | `frontend/app/(auth)/login/page.tsx:27`, `backend/app/main.py:48` | Poor UX; validate against an authenticated endpoint instead. |
| M5 | **Concurrent same-account selection (TOCTOU).** Selection (SELECT LRU active) and INCR aren't atomic; `last_used_at` is written only at job completion, so two workers can grab the same LRU account. | `_sync_helpers.py:126` | Two jobs hammer one account in parallel while others idle; skews rate limiting. Fix: lease/`UPDATE … RETURNING` at checkout. |
| M6 | **`next lint` deprecated** in Next 15 (removed in 16). | `frontend/package.json:9` | CI frontend lint will break on the next major; migrate to ESLint flat config. |
| M7 | **Dead deps / scaffolding.** 5× `@radix-ui/*` + `class-variance-authority` unused; `cn()` never called; `generate-types`/`types/` never used. | `frontend/package.json`, `frontend/lib/utils.ts` | Bloat + a false "shadcn/ui" claim (now removed from docs). Either adopt shadcn or drop the deps. |

## 🟡 Low

- **L1** Dashboard progress bar always 100% — `progressPct(scraped, scraped)`; `JobSummary` has no `total_count`. `frontend/app/page.tsx:130`.
- **L2** Duplicated `exportUrl` in the prospects page (unused `key`, ignores `has_phone`). `frontend/app/jobs/[id]/prospects/page.tsx:30`.
- **L3** No tests for `pause`/`resume`/`DELETE /jobs` or the 307 behavior. `backend/tests/`.
- **L4** `JobRead.mode/status` typed as `str` instead of the enums — loses allowed-values in OpenAPI. `backend/app/schemas/job.py:53`.
- **L5** Duplicated pool logic: async `account_pool.py` (unused by workers) vs sync `_sync_helpers.py`. Consolidate; hoist the hardcoded `-20` margin into config.
- **L6** `Job.total_count`/`max_count` never wired into `_run_scrape` — scrapes are always unbounded. `workers/tasks.py:51`.
- **L7** Frontend Dockerfile uses `node:20-alpine` while CI uses node 22 — align to avoid skew.
- **L8** Commenters caps silently at 500 (no pagination loop). `scraper/client.py:127`.

## ✅ Verified good (no action)

- All 6 "Security by design" rules enforced in app code (`X-API-Key` via `secrets.compare_digest`, session-only auth, `session_json` excluded from reads, non-root containers, env-only secrets). The one exception (a hardcoded test DB password in `conftest.py`) was fixed in this pass — **rotate `91798a77…` if it was ever a real credential** (it's in git history).
- Anti-ban rules 1, 3, 4, 5 correctly implemented; all three job modes are real (no stubs).
- Compose/Docker production topology matches CLAUDE.md exactly (networks, `traefik.docker.network` pin, expose-not-ports, unique aliases, disabled worker/beat healthchecks).
- `.env.example` ↔ `config.py` fully in sync.

## Suggested order of work

1. **H1** (cooldown reactivation — a Celery beat task or lazy check in `get_account_sync`) — unblocks sustained scraping.
2. **H3** + a `session_expired` account state — stops the re-auth blind spot.
3. **H2** (per-request counter) — makes the rate cap real.
4. **H4** (export auth) — restores a user-facing feature.
5. **M1** (resume/retry cursor + `(job_id, ig_pk)` uniqueness) — correctness of counts.
6. The rest as capacity allows.
