from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    with patch("app.main.AsyncSessionLocal") as mock_db,          patch("app.main.get_redis_client") as mock_redis:

        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock()
        mock_redis.return_value = AsyncMock()
        mock_redis.return_value.ping = AsyncMock()

        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    """Health endpoint must work without API key (for Docker healthcheck)."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as no_auth:
        resp = await no_auth.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_requires_api_key(client):
    """Protected routes must return 401 without API key."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        follow_redirects=True,
    ) as no_auth:
        resp = await no_auth.get("/api/v1/jobs/")
    assert resp.status_code in (401, 403)
