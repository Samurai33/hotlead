from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hotlead",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,               # only ack after task completes
    worker_prefetch_multiplier=1,      # one task at a time per worker
    task_routes={
        "app.workers.tasks.*": {"queue": "scraping"},
    },
    broker_connection_retry_on_startup=True,
)
