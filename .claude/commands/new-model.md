---
description: Create a new SQLAlchemy model + Pydantic schemas + Alembic migration + tests
argument-hint: <ModelName> <field:type ...>
---

Create a complete new data model for HotLead: **$ARGUMENTS**

Delegate to the `backend-dev` agent. Steps, in order:

1. Model in `backend/app/models/<snake_name>.py` — inherit from `Base` (`app/models/base.py`), UUID pk, `created_at`/`updated_at` from the mixin. Register the import in `app/models/__init__.py`.
2. Pydantic v2 schemas in `backend/app/schemas/<snake_name>.py`: `<Name>Create`, `<Name>Read`, `<Name>Update` (partial). `Read` uses `model_config = ConfigDict(from_attributes=True)`. Never expose sensitive fields (follow the `session_json` precedent).
3. Alembic migration in `backend/alembic/versions/` — next sequential number (e.g. `003_add_<snake_name>.py`), with working `upgrade()` AND `downgrade()`.
4. Tests in `backend/tests/test_<snake_name>.py` following `conftest.py` patterns.
5. Verify: `ruff check app/ tests/` + `pytest tests/ -x -q` must pass.

Do not create API endpoints — that's `/new-endpoint`.
