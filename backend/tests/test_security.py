import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.core.config import get_settings
from app.main import app


@pytest.mark.asyncio
async def test_health_no_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_jobs_no_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/jobs/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_accounts_no_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/accounts/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_wrong_key_rejected():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": "wrong-key"}
    ) as c:
        resp = await c.get("/api/v1/jobs/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_correct_key_accepted(client):
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200


def test_secrets_are_secretstr_not_plain_str():
    """audit AUDIT-2.md M8: SecretStr masks these in repr()/tracebacks/
    accidental logging -- a plain str secret leaks in a stack trace the
    instant it's interpolated into any exception message."""
    settings = get_settings()
    assert isinstance(settings.api_key, SecretStr)
    assert isinstance(settings.secret_key, SecretStr)
    assert isinstance(settings.session_encryption_key, SecretStr)
    assert isinstance(settings.postgres_password, SecretStr)
    assert settings.api_key.get_secret_value() not in repr(settings.api_key)
