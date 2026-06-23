import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_create_job(client):
    with patch("app.api.v1.jobs.scrape_followers") as mock_task:
        mock_task.apply_async.return_value = MagicMock(id="celery-task-123")
        resp = await client.post("/api/v1/jobs", json={
            "profile_username": "cozinha4e20",
            "mode": "followers",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["profile_username"] == "cozinha4e20"
    assert data["mode"] == "followers"
    assert data["status"] in ("pending", "running")


@pytest.mark.asyncio
async def test_create_job_strips_at_symbol(client):
    with patch("app.api.v1.jobs.scrape_followers") as mock_task:
        mock_task.apply_async.return_value = MagicMock(id="celery-task-456")
        resp = await client.post("/api/v1/jobs", json={
            "profile_username": "@cozinha4e20",
        })

    assert resp.status_code == 201
    assert resp.json()["profile_username"] == "cozinha4e20"


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    import uuid
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_empty(client):
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_requires_api_key(client):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    # Request without API key
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as no_auth:
        resp = await no_auth.post("/api/v1/jobs", json={"profile_username": "test"})
    assert resp.status_code in (401, 403)
