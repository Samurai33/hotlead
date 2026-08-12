"""_run_scrape task-level wiring (audit L6): a job that already hit its
user-set total_count must finish without touching the account pool at all —
this is the highest-risk bit of new logic in the max_count wiring (a bug
here means a capped, already-complete job keeps re-checking out accounts on
every retry/resume instead of just finishing).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.scraper.client import RateLimitExceeded
from app.workers.tasks import _run_scrape


def _mock_sync_helpers(job):
    db = MagicMock()

    get_sync_db = MagicMock()
    get_sync_db.return_value.__enter__.return_value = db
    get_sync_db.return_value.__exit__.return_value = False

    get_sync_redis = MagicMock()
    get_sync_redis.return_value.__enter__.return_value = MagicMock()
    get_sync_redis.return_value.__exit__.return_value = False

    mocks = {
        "get_sync_db": get_sync_db,
        "get_sync_redis": get_sync_redis,
        "get_job": MagicMock(return_value=job),
        "update_job_status": MagicMock(),
        "get_account_sync": MagicMock(),
    }
    return db, mocks


def test_run_scrape_finishes_without_account_when_target_already_reached():
    job = MagicMock(id="job1", total_count=100, scraped_count=100, status="pending")
    db, mocks = _mock_sync_helpers(job)

    with patch.multiple("app.workers._sync_helpers", **mocks):
        result = _run_scrape(MagicMock(), "job1", "someprofile", "iter_followers")

    assert result == {"status": "done", "job_id": "job1"}
    mocks["get_account_sync"].assert_not_called()
    mocks["update_job_status"].assert_any_call(db, "job1", "done")


def test_run_scrape_proceeds_when_target_not_yet_reached():
    job = MagicMock(id="job1", total_count=100, scraped_count=40, status="pending")
    db, mocks = _mock_sync_helpers(job)
    mocks["get_account_sync"].side_effect = RuntimeError("No active Instagram accounts.")

    with patch.multiple("app.workers._sync_helpers", **mocks):
        result = _run_scrape(MagicMock(), "job1", "someprofile", "iter_followers")

    mocks["get_account_sync"].assert_called_once()
    assert result == {"status": "error", "detail": "No active Instagram accounts."}


def test_run_scrape_paused_during_retry_backoff_stays_paused():
    """audit S2 / issue #121: a Celery retry's countdown leaves job.status
    "running" while the task sleeps. If the user pauses during that window,
    pause_job's only guard (status == "running") still passes and flips the
    row to "paused". When the scheduled retry fires and _run_scrape
    re-enters, it must see that "paused" status and bail out immediately —
    not overwrite it back to "running" before the per-iteration pause check
    further down ever gets a chance to run."""
    job = MagicMock(id="job1", total_count=0, scraped_count=0, status="paused")
    db, mocks = _mock_sync_helpers(job)

    with patch.multiple("app.workers._sync_helpers", **mocks):
        result = _run_scrape(MagicMock(), "job1", "someprofile", "iter_followers")

    assert result == {"status": "paused", "job_id": "job1"}
    mocks["get_account_sync"].assert_not_called()
    # Must never re-force the row back to "running".
    for call in mocks["update_job_status"].call_args_list:
        assert call.args[2] != "running"


def test_run_scrape_unbounded_job_proceeds_regardless_of_scraped_count():
    """total_count=0 means unlimited (audit L6's default) — must never
    early-exit no matter how many prospects are already saved."""
    job = MagicMock(id="job1", total_count=0, scraped_count=99999, status="pending")
    db, mocks = _mock_sync_helpers(job)
    mocks["get_account_sync"].side_effect = RuntimeError("No active Instagram accounts.")

    with patch.multiple("app.workers._sync_helpers", **mocks):
        _run_scrape(MagicMock(), "job1", "someprofile", "iter_followers")

    mocks["get_account_sync"].assert_called_once()


def _mock_sync_helpers_with_account(job, client):
    """Extends _mock_sync_helpers with a successful account checkout and all
    the account-lifecycle helpers _run_scrape's except blocks call, so tests
    can exercise the RateLimitExceeded/retry path end to end.
    """
    db, mocks = _mock_sync_helpers(job)
    account = MagicMock(id=uuid.uuid4(), username="acct1")
    mocks["get_account_sync"] = MagicMock(return_value=(account, client))
    mocks["mark_account_cooldown_sync"] = MagicMock()
    mocks["mark_account_challenged_sync"] = MagicMock()
    mocks["mark_account_session_expired_sync"] = MagicMock()
    mocks["save_session_sync"] = MagicMock()
    mocks["save_prospect_batch"] = MagicMock(return_value={"inserted": 0, "emails": 0, "phones": 0})
    mocks["update_job_cursor"] = MagicMock()
    return db, mocks, account


def test_rate_limit_exceeded_cools_down_account_and_schedules_retry():
    """audit C1 / issue #120: RetryError (instagrapi's exhausted-429-retry
    error, mapped by IGClient to RateLimitExceeded — see test_client.py's
    test_*_maps_retry_error_to_rate_limit_exceeded) must drive the exact same
    cooldown + rotation path here as RateLimitError/PleaseWaitFewMinutes
    already do, one level up in the task."""
    job = MagicMock(id="job1", total_count=0, scraped_count=0, status="pending", scrape_cursor=None)
    client = MagicMock()
    client.iter_followers.side_effect = RateLimitExceeded("Rate limit on @acct1")
    db, mocks, account = _mock_sync_helpers_with_account(job, client)

    task = MagicMock()
    task.retry.side_effect = Retry()  # simulates a normally-scheduled retry (budget not exhausted)

    with patch.multiple("app.workers._sync_helpers", **mocks), pytest.raises(Retry):
        _run_scrape(task, "job1", "someprofile", "iter_followers")

    args, _ = mocks["mark_account_cooldown_sync"].call_args
    assert args[0] is db
    assert args[2] is account
    _, retry_kwargs = task.retry.call_args
    assert retry_kwargs["max_retries"] == 3
    assert isinstance(retry_kwargs["exc"], RateLimitExceeded)
    # The job must not have been marked "error" — this retry attempt still
    # has budget left, so it should stay in-flight, not terminate.
    for call in mocks["update_job_status"].call_args_list:
        assert call.args[2] != "error"


def test_exhausted_retries_land_job_in_error_state_with_message():
    """audit S1 / issue #119: once Celery's retry budget is exhausted,
    Task.retry re-raises the original exception directly instead of a Retry
    signal -- before this fix that escaped _run_scrape uncaught, leaving
    job.status stuck at "running" with no error_message ever persisted."""
    job = MagicMock(id="job1", total_count=0, scraped_count=0, status="pending", scrape_cursor=None)
    client = MagicMock()
    original_exc = RateLimitExceeded("Rate limit on @acct1")
    client.iter_followers.side_effect = original_exc
    db, mocks, account = _mock_sync_helpers_with_account(job, client)

    task = MagicMock()
    # Celery's real behavior once max_retries is exceeded: retry() re-raises
    # the original exc directly (see celery.app.task.Task.retry's
    # raise_with_context(exc) branch), not a Retry signal.
    task.retry.side_effect = original_exc

    with patch.multiple("app.workers._sync_helpers", **mocks), pytest.raises(RateLimitExceeded):
        _run_scrape(task, "job1", "someprofile", "iter_followers")

    mocks["mark_account_cooldown_sync"].assert_called_once()
    mocks["update_job_status"].assert_any_call(
        db, "job1", "error", error_message=str(original_exc)[:500]
    )
