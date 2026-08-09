"""_run_scrape task-level wiring (audit L6): a job that already hit its
user-set total_count must finish without touching the account pool at all —
this is the highest-risk bit of new logic in the max_count wiring (a bug
here means a capped, already-complete job keeps re-checking out accounts on
every retry/resume instead of just finishing).
"""

from unittest.mock import MagicMock, patch

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


def test_run_scrape_unbounded_job_proceeds_regardless_of_scraped_count():
    """total_count=0 means unlimited (audit L6's default) — must never
    early-exit no matter how many prospects are already saved."""
    job = MagicMock(id="job1", total_count=0, scraped_count=99999, status="pending")
    db, mocks = _mock_sync_helpers(job)
    mocks["get_account_sync"].side_effect = RuntimeError("No active Instagram accounts.")

    with patch.multiple("app.workers._sync_helpers", **mocks):
        _run_scrape(MagicMock(), "job1", "someprofile", "iter_followers")

    mocks["get_account_sync"].assert_called_once()
