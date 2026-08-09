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


@pytest.mark.asyncio
async def test_baseline_security_headers_present():
    """audit AUDIT-2.md M11: TLS terminates at Cloudflare, which doesn't add
    HSTS without an explicit toggle -- no layer in the chain otherwise
    guarantees these end-to-end."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


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
