import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.account import AccountStatus
from app.schemas.account import AccountRead


def _base_kwargs(**overrides):
    kwargs = {
        "id": uuid.uuid4(),
        "username": "schema_test_x1",
        "proxy_url": "http://user:pass@proxy.example.com:8080",
        "locale": None,
        "status": AccountStatus.active,
        "requests_today": 0,
        "last_used_at": None,
        "cooldown_until": None,
        "created_at": datetime.now(UTC),
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_status_round_trips_as_enum():
    """audit B4: AccountRead.status must be the real AccountStatus enum
    (JobRead/JobListRead already do this for JobMode/JobStatus) rather than a
    plain str that would accept any garbage value."""
    account = AccountRead(**_base_kwargs(status="cooldown"))
    assert account.status == AccountStatus.cooldown
    assert isinstance(account.status, AccountStatus)


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        AccountRead(**_base_kwargs(status="not_a_real_status"))
