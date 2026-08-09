from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

_broker_url = settings.redis_url
_result_backend = settings.redis_url
if _broker_url.startswith(("fakeredis://", "fakeredis+")):
    # kombu has no fakeredis transport — local dev enqueues to an in-process broker
    _broker_url = "memory://"
    _result_backend = "cache+memory://"

celery_app = Celery(
    "hotlead",
    broker=_broker_url,
    backend=_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # only ack after task completes
    worker_prefetch_multiplier=1,  # one task at a time per worker
    task_routes={
        "app.workers.tasks.*": {"queue": "scraping"},
    },
    broker_connection_retry_on_startup=True,
    # Safety net on top of IGClient's per-request timeout (audit AUDIT-2.md
    # M7): with worker_prefetch_multiplier=1, a task that never raises just
    # parks that worker's only slot forever with no operator signal.
    # Generous enough not to kill a legitimately large scrape -- this is a
    # backstop, not a normal-case limit.
    task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
    task_time_limit=settings.celery_task_time_limit_seconds,
)


@worker_process_init.connect
def _dispose_sync_engine_after_fork(**kwargs) -> None:
    """Explicit fork-safety hook (audit AUDIT-2.md H8) -- see
    _sync_helpers.dispose_sync_engine's docstring for why this needs to
    exist at all. Deferred import so this module itself never becomes the
    thing that creates the sync engine before fork.
    """
    from app.workers._sync_helpers import dispose_sync_engine

    dispose_sync_engine()
