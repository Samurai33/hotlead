import uuid

import pytest


@pytest.mark.asyncio
async def test_add_account(client):
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "test_account_x1",
            "session_json": '{"device_id": "test"}',
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "test_account_x1"
    assert "session_json" not in data


@pytest.mark.asyncio
async def test_add_duplicate_account(client):
    await client.post(
        "/api/v1/accounts",
        json={
            "username": "duplicate_acc_x1",
            "session_json": '{"device_id": "test1"}',
        },
    )
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "duplicate_acc_x1",
            "session_json": '{"device_id": "test2"}',
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_accounts(client):
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_session_json_never_exposed(client):
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "secret_acc_x1",
            "session_json": '{"password_equivalent": "NEVER_LEAK_THIS"}',
        },
    )
    assert resp.status_code == 201
    assert "NEVER_LEAK_THIS" not in resp.text
    assert "session_json" not in resp.json()


@pytest.mark.asyncio
async def test_delete_account(client):
    add = await client.post(
        "/api/v1/accounts",
        json={
            "username": "to_delete_x1",
            "session_json": '{"device_id": "test"}',
        },
    )
    acc_id = add.json()["id"]
    resp = await client.delete(f"/api/v1/accounts/{acc_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent(client):
    resp = await client.delete(f"/api/v1/accounts/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_account_slashless_no_redirect(client):
    """Regression guard, same reasoning as test_jobs.test_create_job_slashless_no_redirect:
    a 307 hop here used to carry a Location: http://... that real browsers block as mixed
    content (Traefik reports scheme=http; TLS terminates at the Cloudflare edge)."""
    resp = await client.post(
        "/api/v1/accounts",
        json={"username": "noredirect_acc_x1", "session_json": '{"device_id": "test"}'},
    )
    assert resp.status_code == 201
    assert resp.history == []


@pytest.mark.asyncio
async def test_list_accounts_slashless_no_redirect(client):
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    assert resp.history == []
