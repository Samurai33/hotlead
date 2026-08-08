import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_prospects_empty(client):
    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t1")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "testuser"})
    job_id = job_resp.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{job_id}/prospects")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_prospects_job_not_found(client):
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}/prospects")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_csv(client):
    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t2")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "csvtest"})
    job_id = job_resp.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{job_id}/export?fmt=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_export_json(client):
    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t3")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "jsontest"})
    job_id = job_resp.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{job_id}/export?fmt=json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_export_invalid_format(client):
    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t4")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "fmttest"})
    job_id = job_resp.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{job_id}/export?fmt=xml")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_no_api_key_rejected(client):
    """Audit H4: the export route has no query-param auth fallback — only the
    X-API-Key header works. Locks in that an unauthenticated <a href download>
    (no header) really does get rejected, not silently served."""
    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t5")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "noauthtest"})
    job_id = job_resp.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
        resp = await anon.get(f"/api/v1/jobs/{job_id}/export?fmt=csv")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_export_has_phone_filter(client, db):
    from app.models.prospect import Prospect

    with patch("app.api.v1.jobs.scrape_followers") as m:
        m.apply_async.return_value = MagicMock(id="t6")
        job_resp = await client.post("/api/v1/jobs", json={"profile_username": "phonetest"})
    job_id = job_resp.json()["id"]

    db.add_all(
        [
            Prospect(job_id=uuid.UUID(job_id), username="has_phone_x1", phone="+5511999999999"),
            Prospect(job_id=uuid.UUID(job_id), username="no_phone_x1", phone=None),
        ]
    )
    await db.commit()

    resp = await client.get(f"/api/v1/jobs/{job_id}/export?fmt=json&has_phone=true")
    assert resp.status_code == 200
    usernames = {p["username"] for p in resp.json()}
    assert usernames == {"has_phone_x1"}
