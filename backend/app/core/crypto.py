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

import hashlib
from functools import lru_cache

import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


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
        try:
            return _fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            # SESSION_ENCRYPTION_KEY rotated/drifted since this row was
            # written (e.g. a DB backup restored under a different .env) --
            # Fernet.decrypt raises InvalidToken for a ciphertext that
            # doesn't verify under the current key, and ValueError for a
            # malformed token (e.g. bad base64) (audit #124/B2). Left
            # uncaught, this used to blow up the *entire* query -- every
            # GET /api/v1/accounts hard-failed with 500 for ALL rows, not
            # just the one whose key drifted. Degrade per-row instead: log
            # a fingerprint identifying *which* ciphertext failed (never the
            # raw ciphertext or key itself -- a sha256 digest of the
            # ciphertext lets an operator correlate this log line with the
            # offending DB row without exposing anything secret) and return
            # None so callers see a missing session_json -- the same shape
            # as an account that was never onboarded -- rather than a crash.
            # No key-rotation/versioning story here by design (out of
            # scope); this only stops one bad key from taking down every row.
            fingerprint = hashlib.sha256(value.encode()).hexdigest()[:16]
            logger.warning(
                "crypto.decrypt_failed",
                column="session_json",
                ciphertext_fingerprint=fingerprint,
            )
            return None
