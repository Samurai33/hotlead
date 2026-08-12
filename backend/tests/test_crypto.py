"""EncryptedText graceful degradation on a key mismatch (audit #124/B2).

Before this fix, SESSION_ENCRYPTION_KEY rotating or drifting from what a row
was actually encrypted under (e.g. a DB backup restored under a different
.env) made Fernet.decrypt raise InvalidToken *uncaught* inside
process_result_value -- which blows up the entire SQLAlchemy row-loading
step, so a single bad row 500s every query that touches the Account model
(GET /api/v1/accounts included), not just the one row.

These tests exercise EncryptedText.process_result_value directly -- no DB
needed, it's a plain TypeDecorator method -- by encrypting under one Fernet
key and decrypting via the module's real (settings-backed) Fernet, which is
necessarily a different key.
"""

from cryptography.fernet import Fernet

from app.core.crypto import EncryptedText

_column = EncryptedText()


def test_round_trip_with_correct_key():
    """Sanity check: the happy path still works before we test the failure path."""
    bound = _column.process_bind_param('{"device_id": "test"}', dialect=None)
    assert bound is not None
    result = _column.process_result_value(bound, dialect=None)
    assert result == '{"device_id": "test"}'


def test_none_passes_through_both_directions():
    assert _column.process_bind_param(None, dialect=None) is None
    assert _column.process_result_value(None, dialect=None) is None


def test_decrypt_under_wrong_key_returns_none_not_raise():
    """The scenario #124 describes: a value encrypted under a *different*
    Fernet key than the one the app is currently configured with must
    degrade to None for that row, not raise and take the whole query down.
    """
    other_key = Fernet.generate_key()
    ciphertext_under_other_key = Fernet(other_key).encrypt(b'{"device_id": "drifted"}').decode()

    result = _column.process_result_value(ciphertext_under_other_key, dialect=None)

    assert result is None


def test_decrypt_malformed_token_returns_none_not_raise():
    """Not just a wrong key -- outright garbage (e.g. truncated/corrupted
    ciphertext) must also degrade gracefully rather than crash the query."""
    result = _column.process_result_value("not-a-valid-fernet-token", dialect=None)

    assert result is None
