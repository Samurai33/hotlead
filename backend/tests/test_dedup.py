"""save_prospect_batch dedup + scrape_cursor persistence (audit M1).

Uses a real sync Session (psycopg2, same DB as the async fixtures) because
ON CONFLICT DO NOTHING + RETURNING is genuine Postgres SQL — a mock can't
exercise it. This mirrors workers/_sync_helpers.py's own sync engine, which
is what Celery workers actually use in production.
"""

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.job import Job
from app.models.prospect import Prospect
from app.workers._sync_helpers import save_prospect_batch, update_job_cursor

settings = get_settings()
_SYNC_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest.fixture
def sync_db():
    engine = create_engine(_SYNC_URL)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def _make_job(sync_db) -> str:
    job = Job(profile_username="dedup_test_x1")
    sync_db.add(job)
    sync_db.commit()
    sync_db.refresh(job)
    return str(job.id)


def test_save_prospect_batch_skips_duplicate_ig_pk(sync_db):
    job_id = _make_job(sync_db)

    result = save_prospect_batch(
        sync_db,
        job_id,
        [
            {"username": "u1", "ig_pk": "111", "email": "u1@x.com"},
            {"username": "u2", "ig_pk": "222", "phone": "+55119999"},
        ],
    )
    assert result == {"inserted": 2, "emails": 1, "phones": 1}

    # Same page re-yielded (pause/resume or a Celery retry re-walking the last
    # in-flight page) plus one genuinely new prospect from the next page.
    result2 = save_prospect_batch(
        sync_db,
        job_id,
        [
            {"username": "u1", "ig_pk": "111", "email": "u1@x.com"},
            {"username": "u3", "ig_pk": "333", "email": "u3@x.com"},
        ],
    )
    assert result2 == {"inserted": 1, "emails": 1, "phones": 0}

    rows = (
        sync_db.execute(select(Prospect).where(Prospect.job_id == uuid.UUID(job_id)))
        .scalars()
        .all()
    )
    assert {p.ig_pk for p in rows} == {"111", "222", "333"}


def test_save_prospect_batch_empty_is_noop(sync_db):
    job_id = _make_job(sync_db)
    assert save_prospect_batch(sync_db, job_id, []) == {"inserted": 0, "emails": 0, "phones": 0}


def test_update_job_cursor_persists(sync_db):
    job_id = _make_job(sync_db)

    update_job_cursor(sync_db, job_id, "abc123")
    sync_db.commit()

    job = sync_db.get(Job, uuid.UUID(job_id))
    assert job.scrape_cursor == "abc123"
