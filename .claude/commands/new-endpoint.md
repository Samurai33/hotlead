---
description: Create a new API endpoint with schema, router registration and tests
argument-hint: <METHOD /api/v1/path> <what it does>
---

Create a new HotLead API endpoint: **$ARGUMENTS**

Delegate to the `backend-dev` agent. Requirements:

1. Route in the matching resource router under `backend/app/api/v1/` (create the router file + register in `app/main.py` only if the resource is new).
2. `X-API-Key` auth via the existing dependency — mandatory, no exceptions (only `/health` is open).
3. Explicit `response_model`, correct status codes (201 create, 204 delete, 404 missing, 409 state conflict).
4. Async `AsyncSession` via `Depends(get_db)`, SQLAlchemy 2.0 `select()` style.
5. Pagination (`limit`/`offset` with bounds) on any list endpoint.
6. Tests in `backend/tests/`: happy path + auth rejected (401/403) + not-found.
7. Verify: `ruff check app/ tests/` + `pytest tests/ -x -q` must pass.
8. Update the API endpoints table in `CLAUDE.md` and `README.md`.
