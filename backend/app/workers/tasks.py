"""
Celery tasks for Instagram scraping.
Each task processes followers in batches, checkpointing progress to DB.
"""
import logging
import uuid
from celery import shared_task

from app.scraper.client import RateLimitExceeded, AccountChallenged

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.tasks.scrape_followers",
)
def scrape_followers(self, job_id: str, profile_username: str) -> dict:
    """
    Scrape followers of a given Instagram profile.
    Runs synchronously (Celery workers are sync by default).
    Uses synchronous DB helpers to avoid async complexity in Celery.
    """
    from app.workers._sync_helpers import (
        get_sync_db,
        get_sync_redis,
        get_job,
        update_job_status,
        save_prospect_batch,
        get_account_sync,
        mark_account_cooldown_sync,
    )

    logger.info(f"[Job {job_id}] Starting scrape of @{profile_username}")

    with get_sync_db() as db, get_sync_redis() as redis:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"[Job {job_id}] Job not found")
            return {"status": "error", "detail": "Job not found"}

        update_job_status(db, job_id, "running")
        account, client = get_account_sync(db, redis)

        try:
            batch = []
            for user_data in client.iter_followers(profile_username):
                # Check if job was paused externally
                current_job = get_job(db, job_id)
                if current_job.status == "paused":
                    logger.info(f"[Job {job_id}] Paused — stopping gracefully")
                    break

                batch.append(user_data)

                # Save every 50 prospects
                if len(batch) >= 50:
                    saved = save_prospect_batch(db, job_id, batch)
                    update_job_status(db, job_id, "running", scraped_delta=len(batch))
                    logger.info(f"[Job {job_id}] Saved batch of {saved}")
                    batch = []

            # Save remaining
            if batch:
                save_prospect_batch(db, job_id, batch)
                update_job_status(db, job_id, "running", scraped_delta=len(batch))

            # Mark done (unless paused)
            final_job = get_job(db, job_id)
            if final_job.status != "paused":
                update_job_status(db, job_id, "done")

            # Persist updated session
            from app.workers._sync_helpers import save_session_sync
            save_session_sync(db, account, client)

            logger.info(f"[Job {job_id}] Completed")
            return {"status": "done"}

        except RateLimitExceeded as exc:
            mark_account_cooldown_sync(db, redis, account)
            logger.warning(f"[Job {job_id}] Rate limit — retrying: {exc}")
            raise self.retry(exc=exc, countdown=120)

        except AccountChallenged as exc:
            mark_account_cooldown_sync(db, redis, account)
            logger.warning(f"[Job {job_id}] Account challenged — retrying: {exc}")
            raise self.retry(exc=exc, countdown=300)

        except Exception as exc:
            logger.exception(f"[Job {job_id}] Unexpected error: {exc}")
            update_job_status(db, job_id, "error", error_message=str(exc))
            raise
