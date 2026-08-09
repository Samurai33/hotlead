"""Proxy credential scrubbing from Job.error_message (audit AUDIT-2.md M2).

Uses a real sync Session (same pattern as test_dedup.py) since
update_job_status commits directly.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.job import Job
from app.workers._sync_helpers import _scrub_credentials, update_job_status

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
    job = Job(profile_username="scrub_test_x1")
    sync_db.add(job)
    sync_db.commit()
    sync_db.refresh(job)
    return str(job.id)


def test_scrub_credentials_strips_proxy_userinfo():
    msg = "ProxyError: connect to http://scraper_user:s3cr3t@203.0.113.5:8080 failed"
    assert _scrub_credentials(msg) == "ProxyError: connect to http://***@203.0.113.5:8080 failed"


def test_scrub_credentials_leaves_plain_urls_alone():
    msg = "GET https://api-hotlead.n3xus.dev/health timed out"
    assert _scrub_credentials(msg) == msg


def test_scrub_credentials_handles_multiple_urls():
    msg = "tried http://u1:p1@proxy1.example.com and http://u2:p2@proxy2.example.com"
    assert (
        _scrub_credentials(msg)
        == "tried http://***@proxy1.example.com and http://***@proxy2.example.com"
    )


def test_update_job_status_scrubs_persisted_error_message(sync_db):
    job_id = _make_job(sync_db)
    update_job_status(
        sync_db,
        job_id,
        "error",
        error_message="ProxyError: http://scraper_user:s3cr3t@203.0.113.5:8080 refused",
    )

    job = sync_db.get(Job, uuid.UUID(job_id))
    assert "s3cr3t" not in job.error_message
    assert "scraper_user" not in job.error_message
    assert "203.0.113.5:8080" in job.error_message
