"""
Celery Beat scheduler configuration.
"""

from celery.schedules import crontab

from src.background.celery_app import celery_app
from src.background.tasks.sync_jobs import (
    poll_synced_jobs_task,
    retry_failed_jobs_task,
    sync_pending_jobs_task,
)
from src.config.settings import settings


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic tasks."""

    # Sync pending jobs every 5 minutes (to meet 5-minute push requirement)
    sender.add_periodic_task(
        crontab(minute="*/5"),
        sync_pending_jobs_task.s(),
        name="sync-pending-jobs-every-5-minutes",
    )

    # Poll synced jobs every 30 minutes for status updates
    sender.add_periodic_task(
        crontab(minute="*/30"),
        poll_synced_jobs_task.s(),
        name="poll-synced-jobs-every-30-minutes",
    )

    # Retry failed jobs every 15 minutes
    sender.add_periodic_task(
        crontab(minute="*/15"),
        retry_failed_jobs_task.s(),
        name="retry-failed-jobs-every-15-minutes",
    )


# Task routing configuration (moved from celery_app.py)
celery_app.conf.task_routes = {
    "src.background.tasks.sync_jobs.*": {"queue": "sync"},
}

# Task rate limiting (moved from celery_app.py)
celery_app.conf.task_annotations = {
    "src.background.tasks.sync_jobs.sync_job_task": {
        "rate_limit": "10/m",  # Max 10 sync jobs per minute
        "time_limit": settings.CELERY_TASK_TIME_LIMIT,
        "soft_time_limit": settings.CELERY_TASK_SOFT_TIME_LIMIT,
    },
    "src.background.tasks.sync_jobs.poll_synced_jobs_task": {
        "rate_limit": "2/m",  # Max 2 polling cycles per minute
        "time_limit": 600,  # 10 minutes timeout
        "soft_time_limit": 480,  # 8 minutes soft timeout
    },
}
