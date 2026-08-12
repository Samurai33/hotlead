"""Settings validation (audit AUDIT-2.md L4): a weak/placeholder SECRET_KEY
or API_KEY must fail fast at startup instead of silently running with a
guessable value.

Also covers audit #123/B1: session_encryption_key gets the same weak-value
check as the other two secrets, *plus* a well-formed-Fernet-key check --
unlike secret_key/api_key (opaque strings), a malformed value here used to
pass startup fine and only blow up later as a bare 500 on the first real
POST /accounts request."""

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings

_VALID_KWARGS = {
    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
    "postgres_password": "x" * 32,
    "secret_key": "x" * 32,
    "api_key": "x" * 32,
    # Must be a real Fernet key, not just 32 arbitrary chars -- session_encryption_key
    # is fed straight into Fernet(...) (see the well-formed-Fernet-key check below).
    "session_encryption_key": Fernet.generate_key().decode(),
}


def test_settings_accepts_strong_secrets():
    Settings(**_VALID_KWARGS)


@pytest.mark.parametrize("field", ["secret_key", "api_key", "session_encryption_key"])
def test_settings_rejects_weak_secret(field):
    kwargs = {**_VALID_KWARGS, field: "too-short"}
    with pytest.raises(ValidationError, match="looks like a weak/placeholder"):
        Settings(**kwargs)


def test_settings_rejects_malformed_session_encryption_key():
    """A value that's long enough to pass the entropy floor but isn't a real
    Fernet key (bad base64, or valid base64 that doesn't decode to 32 bytes)
    must still fail fast at startup (audit #123/B1)."""
    kwargs = {**_VALID_KWARGS, "session_encryption_key": "not-a-real-fernet-key" * 2}
    with pytest.raises(ValidationError, match="not a valid Fernet key"):
        Settings(**kwargs)


def test_settings_rejects_placeholder_session_encryption_key():
    """The .env.example default ("CHANGE_ME") must never silently pass startup."""
    kwargs = {**_VALID_KWARGS, "session_encryption_key": "CHANGE_ME"}
    with pytest.raises(ValidationError, match="looks like a weak/placeholder"):
        Settings(**kwargs)
