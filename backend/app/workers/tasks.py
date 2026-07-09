"""
Celery tasks for Instagram scraping.
Processes users in batches of 50, checkpointing after each batch.
Supports pause/resume by checking job.status on every iteration.
"""

import logging
from collections.abc import Generator

from celery import shared_task

from app.scraper.client import AccountChallenged, RateLimitExceeded, SessionExpired

logger = logging.getLogger(__name__)


def _run_scrape(self, job_id: str, target: str, iterator_name: str) -> dict:
    """Shared scraping loop used by all mode-specific tasks.

    target — profile_username for followers/following, post_url for commenters.
    iterator_name — method name on IGClient to call with target as first arg.
    """
    from app.workers._sync_helpers import (
        get_account_sync,
        get_job,
        get_sync_db,
        get_sync_redis,
        mark_account_cooldown_sync,
        mark_account_session_expired_sync,
        save_prospect_batch,
        save_session_sync,
        update_job_status,
    )

    logger.info(f"[Job {job_id}] Starting ({iterator_name}): {target}")

    with get_sync_db() as db, get_sync_redis() as redis:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"[Job {job_id}] Not found")
            return {"status": "error", "detail": "Job not found"}

        update_job_status(db, job_id, "running")

        try:
            account, client = get_account_sync(db, redis)
        except RuntimeError as exc:
            update_job_status(db, job_id, "error", error_message=str(exc))
            return {"status": "error", "detail": str(exc)}

        try:
            iterator: Generator = getattr(client, iterator_name)(target)
            batch: list[dict] = []

            for user_data in iterator:
                current = get_job(db, job_id)
                if current and current.status == "paused":
                    logger.info(f"[Job {job_id}] Paused gracefully")
                    if batch:
                        save_prospect_batch(db, job_id, batch)
                        update_job_status(db, job_id, "paused", scraped_delta=len(batch))
                    break

                batch.append(user_data)

                if len(batch) >= 50:
                    save_prospect_batch(db, job_id, batch)
                    update_job_status(db, job_id, "running", scraped_delta=len(batch))
                    logger.info(f"[Job {job_id}] Batch saved: {len(batch)}")
                    batch = []

            if batch:
                save_prospect_batch(db, job_id, batch)
                update_job_status(db, job_id, "running", scraped_delta=len(batch))

            final = get_job(db, job_id)
            if final and final.status != "paused":
                update_job_status(db, job_id, "done")
                logger.info(f"[Job {job_id}] Done")

            save_session_sync(db, account, client)
            return {"status": "done", "job_id": job_id}

        except RateLimitExceeded as exc:
            mark_account_cooldown_sync(db, redis, account)
            logger.warning(f"[Job {job_id}] Rate limit, retry 120s")
            raise self.retry(exc=exc, countdown=120, max_retries=3)

        except AccountChallenged as exc:
            mark_account_cooldown_sync(db, redis, account)
            logger.warning(f"[Job {job_id}] Challenge, retry 300s")
            raise self.retry(exc=exc, countdown=300, max_retries=2)

        except SessionExpired:
            # Session is dead — no timed recovery. Do NOT retry; flag for re-onboard.
            mark_account_session_expired_sync(db, account)
            msg = f"Session expired for @{account.username} — re-onboard via add_account.py"
            logger.error(f"[Job {job_id}] {msg}")
            update_job_status(db, job_id, "error", error_message=msg)
            return {"status": "error", "detail": msg}

        except Exception as exc:
            logger.exception(f"[Job {job_id}] Error: {exc}")
            update_job_status(db, job_id, "error", error_message=str(exc)[:500])
            raise


@shared_task(bind=True, max_retries=3, name="app.workers.tasks.scrape_followers")
def scrape_followers(self, job_id: str, profile_username: str) -> dict:
    """Scrape followers of a public Instagram profile."""
    return _run_scrape(self, job_id, profile_username, "iter_followers")


@shared_task(bind=True, max_retries=3, name="app.workers.tasks.scrape_following")
def scrape_following(self, job_id: str, profile_username: str) -> dict:
    """Scrape accounts followed by a public Instagram profile."""
    return _run_scrape(self, job_id, profile_username, "iter_following")


@shared_task(bind=True, max_retries=3, name="app.workers.tasks.scrape_commenters")
def scrape_commenters(self, job_id: str, post_url: str) -> dict:
    """Scrape unique commenters from a public Instagram post URL."""
    return _run_scrape(self, job_id, post_url, "iter_commenters")
