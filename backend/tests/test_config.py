"""Settings validation (audit AUDIT-2.md L4): a weak/placeholder SECRET_KEY
or API_KEY must fail fast at startup instead of silently running with a
guessable value."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_VALID_KWARGS = {
    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
    "postgres_password": "x" * 32,
    "secret_key": "x" * 32,
    "api_key": "x" * 32,
    "session_encryption_key": "x" * 32,
}


def test_settings_accepts_strong_secrets():
    Settings(**_VALID_KWARGS)


@pytest.mark.parametrize("field", ["secret_key", "api_key"])
def test_settings_rejects_weak_secret(field):
    kwargs = {**_VALID_KWARGS, field: "too-short"}
    with pytest.raises(ValidationError, match="looks like a weak/placeholder"):
        Settings(**kwargs)
