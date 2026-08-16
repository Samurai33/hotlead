"""Retry jitter and task time limits (audit AUDIT-2.md M6/M7)."""

from app.core.config import get_settings
from app.workers.tasks import _jittered


def test_jittered_stays_within_up_to_25_percent_above_base():
    """audit M6: a pool-wide rate-limit event must not retry every in-flight
    job in lockstep at the exact same instant."""
    base = 120
    for _ in range(200):
        countdown = _jittered(base)
        assert base <= countdown <= base * 1.25


def test_jittered_produces_varying_countdowns():
    countdowns = {round(_jittered(300), 4) for _ in range(50)}
    assert len(countdowns) > 1


def test_jittered_backs_off_exponentially_per_retry():
    """audit AUDIT-3.md H2: jitter alone doesn't stop every attempt of a
    given retry drawing from the same fixed window -- each successive
    `retries` count must at least double the base window (2**retries),
    matching Celery's own retry_backoff growth curve."""
    base = 120
    for retries in range(4):
        for _ in range(50):
            countdown = _jittered(base, retries)
            lower = base * (2**retries)
            upper = lower * 1.25
            assert lower <= countdown <= upper


def test_celery_task_time_limits_configured():
    """audit M7: with worker_prefetch_multiplier=1, a task that never raises
    parks that worker's only slot forever with no operator signal."""
    from app.workers.celery_app import celery_app

    settings = get_settings()
    assert celery_app.conf.task_soft_time_limit == settings.celery_task_soft_time_limit_seconds
    assert celery_app.conf.task_time_limit == settings.celery_task_time_limit_seconds
    assert celery_app.conf.task_soft_time_limit < celery_app.conf.task_time_limit
