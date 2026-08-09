"""Encryption at rest for sensitive DB columns (audit C2).

An Instagram session_json is a live, working credential -- the whole point
of instagrapi's session save/load pattern is that it skips login() entirely.
Storing it as plaintext means a DB dump or backup leak hands over working
sessions for every pooled account, the same blast radius as leaking a
password. This wraps it in a SQLAlchemy TypeDecorator (the pattern
SQLAlchemy's own docs use for "Encrypted Columns") so encryption/decryption
is transparent at the ORM boundary -- application code still reads and
writes plain session_json strings.
"""

from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.session_encryption_key.get_secret_value().encode())


class EncryptedText(TypeDecorator):
    """Text column encrypted at rest with Fernet (symmetric, authenticated)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet().decrypt(value.encode()).decode()
