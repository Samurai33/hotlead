import uuid
from unittest.mock import MagicMock, patch

import pytest


async def _create_job(client, **overrides) -> str:
    payload = {"profile_username": "pausetest_x1", **overrides}
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-lifecycle")
        mock_get_task.return_value = mock_task
        resp = await client.post("/api/v1/jobs", json=payload)
    return resp.json()["id"]


async def _set_status(db, job_id: str, status: str) -> None:
    from app.models.job import Job

    job = await db.get(Job, uuid.UUID(job_id))
    job.status = status
    await db.commit()


@pytest.mark.asyncio
async def test_create_job_followers_dispatches_scrape_followers(client):
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-123")
        mock_get_task.return_value = mock_task
        resp = await client.post(
            "/api/v1/jobs",
            json={
                "profile_username": "cozinha4e20",
                "mode": "followers",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["profile_username"] == "cozinha4e20"
    assert data["mode"] == "followers"
    assert data["status"] in ("pending", "running")
    mock_get_task.assert_called_once_with("followers")


@pytest.mark.asyncio
async def test_create_job_following_dispatches_scrape_following(client):
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-456")
        mock_get_task.return_value = mock_task
        resp = await client.post(
            "/api/v1/jobs",
            json={
                "profile_username": "cozinha4e20",
                "mode": "following",
            },
        )

    assert resp.status_code == 201
    assert resp.json()["mode"] == "following"
    mock_get_task.assert_called_once_with("following")


@pytest.mark.asyncio
async def test_create_job_commenters_dispatches_scrape_commenters(client):
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-789")
        mock_get_task.return_value = mock_task
        resp = await client.post(
            "/api/v1/jobs",
            json={
                "profile_username": "cozinha4e20",
                "mode": "commenters",
                "target_post_url": "https://www.instagram.com/p/ABC123/",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["mode"] == "commenters"
    assert data["target_post_url"] == "https://www.instagram.com/p/ABC123/"
    mock_get_task.assert_called_once_with("commenters")
    mock_task.apply_async.assert_called_once_with(
        args=[data["id"], "https://www.instagram.com/p/ABC123/"],
        queue="scraping",
    )


@pytest.mark.asyncio
async def test_get_task_for_mode_returns_correct_tasks():
    from app.api.v1.jobs import _get_task_for_mode

    with (
        patch("app.api.v1.jobs._get_scrape_followers_task", return_value="followers-task"),
        patch("app.api.v1.jobs._get_scrape_following_task", return_value="following-task"),
        patch("app.api.v1.jobs._get_scrape_commenters_task", return_value="commenters-task"),
    ):
        assert _get_task_for_mode("followers") == "followers-task"
        assert _get_task_for_mode("following") == "following-task"
        assert _get_task_for_mode("commenters") == "commenters-task"


@pytest.mark.asyncio
async def test_create_job_strips_at_symbol(client):
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-789")
        mock_get_task.return_value = mock_task
        resp = await client.post(
            "/api/v1/jobs",
            json={
                "profile_username": "@cozinha4e20",
            },
        )

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
async def test_create_job_slashless_no_redirect(client):
    """Regression guard: POST /api/v1/jobs (no trailing slash) must hit the
    route directly, not 307-redirect to /api/v1/jobs/. In production Traefik
    reports scheme=http to this app (TLS terminates at the Cloudflare edge),
    so that redirect's Location was http://... — browsers block that as mixed
    content, breaking job creation outright. httpx's ASGI transport doesn't
    care about scheme, so only `resp.history` (the redirect hop itself)
    catches this — status 201 alone would pass even with the old bug."""
    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-noredirect")
        mock_get_task.return_value = mock_task
        resp = await client.post(
            "/api/v1/jobs",
            json={"profile_username": "noredirecttest", "mode": "followers"},
        )
    assert resp.status_code == 201
    assert resp.history == []


@pytest.mark.asyncio
async def test_list_jobs_slashless_no_redirect(client):
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert resp.history == []


@pytest.mark.asyncio
async def test_pause_running_job(client, db):
    job_id = await _create_job(client)
    await _set_status(db, job_id, "running")

    resp = await client.post(f"/api/v1/jobs/{job_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_non_running_job_rejected(client):
    # freshly created jobs are "pending", not "running"
    job_id = await _create_job(client)
    resp = await client.post(f"/api/v1/jobs/{job_id}/pause")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pause_not_found(client):
    resp = await client.post(f"/api/v1/jobs/{uuid.uuid4()}/pause")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resume_paused_job_redispatches(client, db):
    job_id = await _create_job(client)
    await _set_status(db, job_id, "paused")

    with patch("app.api.v1.jobs._get_task_for_mode") as mock_get_task:
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="celery-task-resumed")
        mock_get_task.return_value = mock_task
        resp = await client.post(f"/api/v1/jobs/{job_id}/resume")

    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    mock_task.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_resume_non_paused_job_rejected(client):
    job_id = await _create_job(client)  # "pending", not "paused"
    resp = await client.post(f"/api/v1/jobs/{job_id}/resume")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_not_found(client):
    resp = await client.post(f"/api/v1/jobs/{uuid.uuid4()}/resume")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_removes_it(client):
    job_id = await _create_job(client)

    with patch("app.workers.celery_app.celery_app"):
        resp = await client.delete(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_not_found(client):
    resp = await client.delete(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_revokes_celery_task(client):
    job_id = await _create_job(client)

    with patch("app.workers.celery_app.celery_app") as mock_celery_app:
        resp = await client.delete(f"/api/v1/jobs/{job_id}")

    assert resp.status_code == 204
    mock_celery_app.control.revoke.assert_called_once_with("celery-task-lifecycle", terminate=True)


@pytest.mark.asyncio
async def test_create_job_with_max_count_sets_total_count(client):
    job_id = await _create_job(client, max_count=250)
    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.json()["total_count"] == 250


@pytest.mark.asyncio
async def test_create_job_without_max_count_defaults_total_count_zero(client):
    job_id = await _create_job(client)
    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.json()["total_count"] == 0


@pytest.mark.asyncio
async def test_create_job_oversized_profile_username_rejected(client):
    """audit B7: profile_username backs a String(100) column -- oversized
    input must 422 from Pydantic, not 500 from an unhandled
    StringDataRightTruncation at INSERT time."""
    resp = await client.post(
        "/api/v1/jobs",
        json={"profile_username": "x" * 101},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_job_oversized_target_post_url_rejected(client):
    """audit B7: target_post_url backs a String(500) column."""
    oversized = "https://www.instagram.com/p/" + ("A" * 480) + "/"
    resp = await client.post(
        "/api/v1/jobs",
        json={
            "profile_username": "cozinha4e20",
            "mode": "commenters",
            "target_post_url": oversized,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_requires_api_key(client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as no_auth:
        resp = await no_auth.post("/api/v1/jobs/", json={"profile_username": "test"})
    assert resp.status_code in (401, 403)
