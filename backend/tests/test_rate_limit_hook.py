"""Per-request rate-limit hook tests (audit H2).

Exercises app.workers._sync_helpers._make_request_hook in isolation: a fake
sync Redis (fakeredis) stands in for the real broker, and the DB session is a
Mock since we only need to assert the requests_today UPDATE was issued, not
persist it. No real Postgres/Redis needed.
"""

import uuid
from unittest.mock import MagicMock

import fakeredis
import pytest

from app.scraper.client import RateLimitExceeded
from app.workers._sync_helpers import _make_request_hook


def _hook(max_req: int = 200):
    redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
    db = MagicMock()
    account_id = uuid.uuid4()
    hook = _make_request_hook(account_id, db, redis_client, max_req)
    return hook, db, redis_client, account_id


def test_hook_increments_per_call_not_per_checkout():
    hook, db, redis_client, account_id = _hook(max_req=200)
    for _ in range(5):
        hook()
    assert int(redis_client.get(f"hotlead:ratelimit:{account_id}")) == 5
    assert db.execute.call_count == 5


def test_hook_stays_under_cap_silently():
    hook, _db, _redis, _id = _hook(max_req=200)
    for _ in range(179):
        hook()  # cap enforced at max_req - 20 = 180; 179 calls must not raise


def test_hook_raises_once_cap_reached():
    hook, _db, redis_client, account_id = _hook(max_req=200)
    with pytest.raises(RateLimitExceeded):
        for _ in range(180):  # 200 - 20 margin
            hook()
    # the raising call still incremented before raising
    assert int(redis_client.get(f"hotlead:ratelimit:{account_id}")) == 180


def test_hook_sets_ttl_on_first_call():
    hook, _db, redis_client, account_id = _hook(max_req=200)
    hook()
    ttl = redis_client.ttl(f"hotlead:ratelimit:{account_id}")
    assert 0 < ttl <= 3600
