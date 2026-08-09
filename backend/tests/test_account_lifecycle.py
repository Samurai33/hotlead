"""Account challenge/ban escalation (audit AUDIT-2.md H2/H3) and cooldown
reactivation (audit AUDIT-2.md L1/L2).

Uses a real sync Session (matches _sync_helpers.py's actual production path,
same pattern as test_dedup.py) since mark_account_challenged_sync and
save_session_sync commit directly.

The cooldown-reactivation tests below mirror what the now-deleted
scraper/account_pool.py's own test file (test_account_pool.py) covered --
that module was a confirmed-dead async twin of this sync path (audit L1),
and its test suite was thoroughly covering the *unused* code while this,
the actual production path, had thinner direct coverage (audit L2).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.account import Account, AccountStatus
from app.workers._sync_helpers import (
    get_account_sync,
    mark_account_challenged_sync,
    mark_account_cooldown_sync,
    reactivate_cooldown_accounts_sync,
    save_session_sync,
)

settings = get_settings()
_SYNC_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest.fixture
def sync_db():
    engine = create_engine(_SYNC_URL)
    session = sessionmaker(bind=engine)()
    try:
        # Each test here commits directly (mark_account_challenged_sync etc.
        # don't roll back), so a row left behind by an earlier test -- or by
        # another file's fixture that also doesn't clean up after itself --
        # would silently become a second candidate for get_account_sync's
        # "no active accounts" assertions below. Clear the slate first.
        session.query(Account).delete()
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def _make_account(sync_db, **kw) -> Account:
    acc = Account(
        username=kw.pop("username", "streak_test_x1"),
        session_json=kw.pop("session_json", '{"device_id": "test"}'),
        proxy_url=kw.pop("proxy_url", "http://user:pass@proxy.example.com:8080"),
        status=kw.pop("status", AccountStatus.active),
        **kw,
    )
    sync_db.add(acc)
    sync_db.commit()
    sync_db.refresh(acc)
    return acc


def test_challenge_increments_streak_and_cools_down(sync_db):
    acc = _make_account(sync_db, username="streak_incr_x1")
    mark_account_challenged_sync(sync_db, None, acc)
    assert acc.challenge_streak == 1
    assert acc.status == AccountStatus.cooldown
    assert acc.cooldown_until is not None


def test_challenge_streak_escalates_to_banned_at_limit(sync_db):
    acc = _make_account(sync_db, username="streak_ban_x1")
    limit = settings.ig_challenge_streak_limit

    for _ in range(limit - 1):
        mark_account_challenged_sync(sync_db, None, acc)
        assert acc.status == AccountStatus.cooldown

    mark_account_challenged_sync(sync_db, None, acc)
    assert acc.challenge_streak == limit
    assert acc.status == AccountStatus.banned
    assert acc.cooldown_until is None


def test_rate_limit_cooldown_does_not_touch_streak(sync_db):
    """audit H3: a plain rate limit is routine and must not push an account
    toward a ban -- only real challenges/flags (mark_account_challenged_sync)
    count toward the streak."""
    acc = _make_account(sync_db, username="streak_ratelimit_x1")
    mark_account_cooldown_sync(sync_db, None, acc)
    assert acc.challenge_streak == 0
    assert acc.status == AccountStatus.cooldown


def test_successful_scrape_resets_streak(sync_db):
    acc = _make_account(sync_db, username="streak_reset_x1", challenge_streak=2)
    client = MagicMock()
    client.get_updated_session.return_value = '{"device_id": "updated"}'

    save_session_sync(sync_db, acc, client)

    assert acc.challenge_streak == 0


def test_past_cooldown_reactivated_sync(sync_db):
    acc = _make_account(
        sync_db,
        username="cd_past_sync_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) - timedelta(minutes=1),
    )
    reactivate_cooldown_accounts_sync(sync_db)
    sync_db.refresh(acc)
    assert acc.status == AccountStatus.active
    assert acc.cooldown_until is None


def test_future_cooldown_stays_sync(sync_db):
    acc = _make_account(
        sync_db,
        username="cd_future_sync_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) + timedelta(minutes=30),
    )
    reactivate_cooldown_accounts_sync(sync_db)
    sync_db.refresh(acc)
    assert acc.status == AccountStatus.cooldown
    assert acc.cooldown_until is not None


def test_session_expired_excluded_from_checkout(sync_db):
    """session_expired has no timed recovery (audit H3) -- unlike cooldown,
    reactivate_cooldown_accounts_sync must never touch it, and get_account_sync
    must never hand it out."""
    _make_account(sync_db, username="expired_sync_x1", status=AccountStatus.session_expired)

    with pytest.raises(RuntimeError, match="No active Instagram accounts"):
        get_account_sync(sync_db, MagicMock(get=MagicMock(return_value=None)))


def test_reactivated_account_then_selectable_via_checkout(sync_db):
    acc = _make_account(
        sync_db,
        username="cd_then_active_sync_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) - timedelta(seconds=1),
    )

    redis_client = MagicMock(get=MagicMock(return_value=None))
    with patch("app.workers._sync_helpers.IGClient", return_value=MagicMock()):
        got_account, _client = get_account_sync(sync_db, redis_client)

    assert got_account.id == acc.id
    assert got_account.status == AccountStatus.active
