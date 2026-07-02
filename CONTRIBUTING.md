# Contributing to HotLead

## Before anything

Read `CLAUDE.md`. It defines the stack, the security rules and the anti-ban rules — none of them are negotiable in a PR.

## Development setup

```bash
git clone https://github.com/Samurai33/hotlead.git && cd hotlead
cp .env.example .env        # fill CHANGE_ME values
./setup.sh                  # or .\setup.ps1 on Windows
make up
make migrate
```

## Workflow

1. Branch from `main`: `feat/<name>`, `fix/<name>` or `chore/<name>`.
2. Make the change. If you use Claude Code, the agents in `.claude/agents/` and commands in `.claude/commands/` encode the project conventions — use them.
3. Quality gates (CI enforces all of these):

```bash
# backend
cd backend && ruff check app/ tests/ && pytest tests/ -x -q

# frontend
cd frontend && npm run build && npx tsc --noEmit
```

4. Model changed? Ship the Alembic migration in the same PR (sequential numbering, working `downgrade()`).
5. New endpoint? Update the API tables in `CLAUDE.md` and `README.md`.
6. Open a PR using the template. One logical change per PR.

## Code style

- **Python**: ruff (config in `backend/pyproject.toml`), SQLAlchemy 2.0 `select()` style, Pydantic v2, full async in the API layer, sync only inside Celery workers.
- **TypeScript**: strict mode, no `any` without a justifying comment, API calls only through `lib/api.ts`.
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

## What will get a PR rejected

- Storing Instagram passwords anywhere, in any form.
- Removing or weakening auth, rate-limit delays, or account rotation.
- Exposing `session_json` in any API response.
- Exposing Postgres/Redis ports in compose files.
- Failing CI.
