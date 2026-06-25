import pytest
import uuid
from unittest.mock import patch, MagicMock


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
