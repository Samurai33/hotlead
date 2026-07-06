from unittest.mock import MagicMock, patch

import pytest


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
async def test_requires_api_key(client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as no_auth:
        resp = await no_auth.post("/api/v1/jobs/", json={"profile_username": "test"})
    assert resp.status_code in (401, 403)
