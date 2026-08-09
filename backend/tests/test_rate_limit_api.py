"""POST /jobs and POST /accounts rate limiting (audit AUDIT-2.md H1).

The shared `client` fixture (conftest.py) overrides rate_limit_writes to a
no-op so the rest of the suite's job/account creation volume never trips
it -- this file builds its own client with the real dependency wired in
instead, and drives api_rate_limit_per_minute down so the test stays fast.
"""

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.core.redis as redis_module
from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.main import app

TEST_API_KEY = "test-api-key-1234"


@pytest.fixture(autouse=True)
def _low_limit(monkeypatch):
    monkeypatch.setattr(get_settings(), "api_rate_limit_per_minute", 3)


@pytest_asyncio.fixture(autouse=True)
async def _fresh_redis_singleton():
    # get_redis_client() caches one client for the whole process, bound to
    # whichever event loop created it -- pytest-asyncio gives each test its
    # own loop, so reusing a client from a prior test breaks with "attached
    # to a different loop" / "Event loop is closed". Force a new one per test.
    await redis_module.close_redis()
    yield
    await redis_module.close_redis()


@pytest_asyncio.fixture
async def rate_limited_client(db):
    # Wipe any bucket left by a prior run in the same shared Redis --
    # buckets self-expire after 60s but a back-to-back run could still race.
    redis_client = await get_redis_client()
    async for key in redis_client.scan_iter("hotlead:apiratelimit:*"):
        await redis_client.delete(key)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_account_creation_throttled_past_limit(rate_limited_client):
    client = rate_limited_client
    statuses = []
    for i in range(4):  # limit is 3 (see _low_limit)
        resp = await client.post(
            "/api/v1/accounts",
            json={
                "username": f"ratelimit_acc_x{i}",
                "session_json": '{"device_id": "test"}',
                "proxy_url": "http://user:pass@proxy.example.com:8080",
            },
        )
        statuses.append(resp.status_code)

    assert statuses[:3] == [201, 201, 201]
    assert statuses[3] == 429


@pytest.mark.asyncio
async def test_job_creation_throttled_past_limit(rate_limited_client):
    client = rate_limited_client
    statuses = []
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_get_task.return_value = MagicMock(
            apply_async=MagicMock(return_value=MagicMock(id="celery-task-ratelimit"))
        )
        for i in range(4):  # limit is 3 (see _low_limit)
            resp = await client.post(
                "/api/v1/jobs",
                json={"profile_username": f"ratelimit_job_x{i}", "mode": "followers"},
            )
            statuses.append(resp.status_code)

    assert statuses[:3] == [201, 201, 201]
    assert statuses[3] == 429


@pytest.mark.asyncio
async def test_buckets_scoped_per_path(rate_limited_client):
    """Hammering /jobs must not also throttle /accounts -- each write route
    gets its own bucket (keyed by IP + path), not one shared global cap."""
    client = rate_limited_client
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_get_task.return_value = MagicMock(
            apply_async=MagicMock(return_value=MagicMock(id="celery-task-scoped"))
        )
        for i in range(3):  # exhausts the /jobs bucket (limit is 3)
            resp = await client.post(
                "/api/v1/jobs",
                json={"profile_username": f"scoped_job_x{i}", "mode": "followers"},
            )
            assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "scoped_acc_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 201
