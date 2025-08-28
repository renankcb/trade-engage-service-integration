"""
Celery application configuration and setup.
"""

import os

from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery configuration
celery_app = Celery(
    "service_integration",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.background.tasks.sync_jobs", "src.background.tasks.cleanup_jobs"],
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "sync_job_task": {"queue": "sync"},
        "sync_pending_jobs_task": {"queue": "sync"},
        "poll_synced_jobs_task": {"queue": "poll"},
        "retry_failed_jobs_task": {"queue": "retry"},
        "retry_failed_job_task": {"queue": "retry"},
        "cleanup_completed_jobs_task": {"queue": "maintenance"},
        "cleanup_failed_jobs_task": {"queue": "maintenance"},
    },
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    # Task configuration
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    task_ignore_result=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Result backend configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
    # Queue configuration
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    # Beat scheduler configuration
    beat_schedule={
        # Sync pending jobs every 2 minutes
        "sync-pending-jobs": {
            "task": "sync_pending_jobs_task",
            "schedule": 120.0,  # 2 minutes
            "options": {"queue": "sync"},
        },
        # Poll for updates every 5 minutes
        "poll-job-updates": {
            "task": "poll_synced_jobs_task",
            "schedule": 300.0,  # 5 minutes
            "options": {"queue": "poll"},
        },
        # Retry failed jobs every 10 minutes
        "retry-failed-jobs": {
            "task": "retry_failed_jobs_task",
            "schedule": 600.0,  # 10 minutes
            "options": {"queue": "retry"},
        },
        # Cleanup completed jobs every hour
        "cleanup-completed-jobs": {
            "task": "cleanup_completed_jobs_task",
            "schedule": crontab(minute=0, hour="*"),  # Every hour
            "options": {"queue": "maintenance"},
        },
        # Cleanup failed jobs every 6 hours
        "cleanup-failed-jobs": {
            "task": "cleanup_failed_jobs_task",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "options": {"queue": "maintenance"},
        },
        # Cleanup outbox events every 12 hours
        "cleanup-outbox-events": {
            "task": "cleanup_outbox_events_task",
            "schedule": crontab(minute=0, hour="*/12"),  # Every 12 hours
            "options": {"queue": "maintenance"},
        },
        # Cleanup orphaned routings daily
        "cleanup-orphaned-routings": {
            "task": "cleanup_orphaned_routings_task",
            "schedule": crontab(minute=0, hour=2),  # Daily at 2 AM
            "options": {"queue": "maintenance"},
        },
    },
    # Worker pool configuration
    worker_pool="prefork",
    worker_concurrency=4,  # Number of worker processes
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Monitoring and metrics
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Security - use environment variable or default
    security_key=os.getenv("SECRET_KEY", "default_secret_key"),
    security_certificate=None,
    security_cert_store=None,
)

# Task annotations for specific tasks
celery_app.conf.task_annotations = {
    "sync_job_task": {
        "rate_limit": "100/m",  # 100 tasks per minute
        "time_limit": 300,  # 5 minutes
        "soft_time_limit": 240,  # 4 minutes
    },
    "sync_pending_jobs_task": {
        "rate_limit": "30/m",  # 30 tasks per minute
        "time_limit": 600,  # 10 minutes
        "soft_time_limit": 480,  # 8 minutes
    },
    "poll_synced_jobs_task": {
        "rate_limit": "12/m",  # 12 tasks per minute (every 5 minutes)
        "time_limit": 900,  # 15 minutes
        "soft_time_limit": 720,  # 12 minutes
    },
    "retry_failed_jobs_task": {
        "rate_limit": "6/m",  # 6 tasks per minute (every 10 minutes)
        "time_limit": 1200,  # 20 minutes
        "soft_time_limit": 900,  # 15 minutes
    },
}

# Import tasks to ensure they are registered
celery_app.autodiscover_tasks(["src.background.tasks"])

if __name__ == "__main__":
    celery_app.start()
