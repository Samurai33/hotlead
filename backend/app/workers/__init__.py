"""Workers package.

Importing ``celery_app`` here guarantees the configured Celery application is
instantiated (and set as the current app) before any ``@shared_task`` in
``tasks.py`` is imported. Without this, a process that imports the tasks without
first importing ``celery_app`` — e.g. the API enqueuing a job right after a
restart — would bind the shared tasks to Celery's default app and publish to the
default ``amqp://`` broker instead of the configured Redis broker.
"""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
