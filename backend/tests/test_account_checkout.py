"""Account checkout atomicity (audit AUDIT-2.md H4).

Uses a real sync Postgres session (same pattern as test_dedup.py /
test_account_lifecycle.py) because `FOR UPDATE SKIP LOCKED` is genuine
Postgres locking behavior — a mock can't exercise it, and that locking is
the entire point of the fix.
"""

import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.account import Account, AccountStatus
from app.workers._sync_helpers import get_account_sync

settings = get_settings()
_SYNC_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest.fixture
def sync_db():
    engine = create_engine(_SYNC_URL)
    session = sessionmaker(bind=engine)()
    try:
        # get_account_sync's WHERE clause has no per-test scoping (it looks
        # at every active account), so a row any earlier test in this file
        # committed and left behind would silently become a second eligible
        # candidate here — clear the slate before every test instead of
        # relying on execution order.
        session.query(Account).delete()
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def _make_account(sync_db, **kw) -> Account:
    acc = Account(
        username=kw.pop("username"),
        session_json=kw.pop("session_json", '{"device_id": "test"}'),
        proxy_url=kw.pop("proxy_url", "http://user:pass@proxy.example.com:8080"),
        status=kw.pop("status", AccountStatus.active),
        **kw,
    )
    sync_db.add(acc)
    sync_db.commit()
    sync_db.refresh(acc)
    return acc


class _Redis:
    """Bare redis stub — no requests recorded yet, so every account reads as
    under the rate cap."""

    def get(self, key):
        return None


@patch("app.workers._sync_helpers.IGClient")
def test_checkout_sets_lease_and_last_used_at(mock_igclient, sync_db):
    acc = _make_account(sync_db, username="checkout_lease_x1")
    mock_igclient.return_value = MagicMock()

    got_account, _client = get_account_sync(sync_db, _Redis())

    assert got_account.id == acc.id
    assert got_account.leased_until is not None
    assert got_account.leased_until > datetime.now(UTC)
    assert got_account.last_used_at is not None


@patch("app.workers._sync_helpers.IGClient")
def test_checkout_passes_account_locale_to_igclient(mock_igclient, sync_db):
    """audit AUDIT-2.md M5: the account's locale (geo-matched to its proxy)
    must reach IGClient so it can set_locale()/set_country() on the
    instagrapi session -- a mismatched device/IP geography is itself a
    detection signal."""
    _make_account(sync_db, username="checkout_locale_x1", locale="pt_BR")
    mock_igclient.return_value = MagicMock()

    get_account_sync(sync_db, _Redis())

    _, kwargs = mock_igclient.call_args
    assert kwargs.get("locale") == "pt_BR"


@patch("app.workers._sync_helpers.IGClient")
def test_leased_account_excluded_from_checkout(mock_igclient, sync_db):
    _make_account(
        sync_db,
        username="checkout_leased_x1",
        leased_until=datetime.now(UTC) + timedelta(minutes=10),
    )

    with pytest.raises(RuntimeError, match="No active Instagram accounts"):
        get_account_sync(sync_db, _Redis())

    mock_igclient.assert_not_called()


@patch("app.workers._sync_helpers.IGClient")
def test_expired_lease_is_reclaimable(mock_igclient, sync_db):
    """A worker that crashed mid-job without clearing leased_until must not
    strand the account forever — audit H4's self-healing TTL."""
    acc = _make_account(
        sync_db,
        username="checkout_expired_lease_x1",
        leased_until=datetime.now(UTC) - timedelta(minutes=1),
    )
    mock_igclient.return_value = MagicMock()

    got_account, _client = get_account_sync(sync_db, _Redis())

    assert got_account.id == acc.id


@patch("app.workers._sync_helpers.IGClient")
def test_all_rate_limited_releases_locks_without_claiming(mock_igclient, sync_db):
    _make_account(sync_db, username="checkout_ratelimited_x1")

    class _MaxedRedis:
        def get(self, key):
            return str(settings.ig_max_requests_per_hour)

    with pytest.raises(RuntimeError, match="All accounts hit rate limits"):
        get_account_sync(sync_db, _MaxedRedis())

    mock_igclient.assert_not_called()

    # The row must not have been claimed (only skipped-past), and must not
    # still be locked for the next caller.
    sync_db.rollback()
    fresh = sync_db.query(Account).filter_by(username="checkout_ratelimited_x1").one()
    assert fresh.leased_until is None


def test_concurrent_checkout_claims_account_exactly_once(sync_db):
    """Proves the actual DB-level race fix: two overlapping transactions
    racing FOR UPDATE SKIP LOCKED on the single active account must not both
    win. Before audit H4's fix (plain SELECT, no locking), both threads here
    would read the same 'idle' account and both would return it.

    Takes the sync_db fixture purely for its accounts-table cleanup — the
    two threads below open their own independent sessions since a Session
    isn't thread-safe.
    """
    engine = create_engine(_SYNC_URL)
    Session = sessionmaker(bind=engine)
    setup_db = Session()
    try:
        _make_account(setup_db, username="checkout_race_x1")
    finally:
        setup_db.close()

    thread_a_holding_lock = threading.Event()
    thread_a_may_release = threading.Event()
    results: dict[str, object] = {}

    class _BlockingRedis:
        """Blocks the FIRST caller's rate-limit check so the second caller's
        own SELECT FOR UPDATE SKIP LOCKED runs while the row is still locked
        (uncommitted) by the first transaction."""

        def get(self, key):
            thread_a_holding_lock.set()
            thread_a_may_release.wait(timeout=5)
            return None

    class _PlainRedis:
        def get(self, key):
            return None

    def run_a():
        db = Session()
        try:
            with patch("app.workers._sync_helpers.IGClient", return_value=MagicMock()):
                account, _client = get_account_sync(db, _BlockingRedis())
                # Read before closing the session below — the ORM object
                # becomes detached afterward and can't lazy-refresh attrs.
                results["a"] = account.username
        except Exception as exc:  # noqa: BLE001 — captured for the assertion below
            results["a"] = exc
        finally:
            db.rollback()
            db.close()

    def run_b():
        assert thread_a_holding_lock.wait(timeout=5), "thread A never reached its lock"
        db = Session()
        try:
            with patch("app.workers._sync_helpers.IGClient", return_value=MagicMock()):
                results["b"] = get_account_sync(db, _PlainRedis())
        except Exception as exc:  # noqa: BLE001 — captured for the assertion below
            results["b"] = exc
        finally:
            db.rollback()
            db.close()
            thread_a_may_release.set()

    ta = threading.Thread(target=run_a)
    tb = threading.Thread(target=run_b)
    ta.start()
    tb.start()
    ta.join(timeout=10)
    tb.join(timeout=10)

    # B raced against A's still-uncommitted lock and must have found nothing
    # claimable — not the same account A ends up with.
    assert isinstance(results["b"], RuntimeError)
    assert "No active Instagram accounts" in str(results["b"])
    assert results["a"] == "checkout_race_x1"

    cleanup_db = Session()
    try:
        cleanup_db.query(Account).filter_by(username="checkout_race_x1").delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()
        engine.dispose()
