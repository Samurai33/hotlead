"""Account-pool tests: cooldown auto-reactivation (H1) and session_expired exclusion (H3).

Exercises the async twin (account_pool) against the DB fixture directly, avoiding
any real Instagram calls. IGClient is never constructed here — we only assert on the
account-selection / reactivation query behavior.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.account import Account, AccountStatus
from app.scraper.account_pool import reactivate_cooldown_accounts


async def _add(db, **kw):
    acc = Account(
        username=kw.pop("username"),
        session_json=kw.pop("session_json", '{"device_id": "test"}'),
        status=kw.pop("status", AccountStatus.active),
        **kw,
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


@pytest.mark.asyncio
async def test_past_cooldown_reactivated(db):
    acc = await _add(
        db,
        username="cd_past_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) - timedelta(minutes=1),
    )
    await reactivate_cooldown_accounts(db)
    await db.refresh(acc)
    assert acc.status == AccountStatus.active
    assert acc.cooldown_until is None


@pytest.mark.asyncio
async def test_future_cooldown_stays(db):
    acc = await _add(
        db,
        username="cd_future_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) + timedelta(minutes=30),
    )
    await reactivate_cooldown_accounts(db)
    await db.refresh(acc)
    assert acc.status == AccountStatus.cooldown
    assert acc.cooldown_until is not None


@pytest.mark.asyncio
async def test_session_expired_excluded_from_selection(db):
    await _add(db, username="expired_x1", status=AccountStatus.session_expired)

    # The selection query used by both get_available_client and get_account_sync.
    result = await db.execute(select(Account).where(Account.status == AccountStatus.active))
    usernames = {a.username for a in result.scalars().all()}
    assert "expired_x1" not in usernames


@pytest.mark.asyncio
async def test_reactivated_account_then_selectable(db):
    acc = await _add(
        db,
        username="cd_then_active_x1",
        status=AccountStatus.cooldown,
        cooldown_until=datetime.now(UTC) - timedelta(seconds=1),
    )
    await reactivate_cooldown_accounts(db)

    result = await db.execute(select(Account).where(Account.status == AccountStatus.active))
    usernames = {a.username for a in result.scalars().all()}
    assert acc.username in usernames
