"""
Celery application configuration and setup.
"""

import os

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery configuration
celery_app = Celery(
    "service_integration",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.background.tasks.sync_jobs", "src.background.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "sync_job_task": {
            "queue": "default"
        },  # Use default queue for immediate processing
        "sync_pending_jobs_task": {"queue": "sync"},
        "poll_synced_jobs_task": {"queue": "poll"},
        "retry_failed_jobs_task": {"queue": "retry"},
        "retry_failed_job_task": {"queue": "retry"},
    },
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    worker_disable_rate_limits=True,  # Prevent event loop issues
    worker_concurrency=4,  # Match docker-compose concurrency
    worker_pool="prefork",
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
    # Priority configuration
    task_default_priority=10,
    # Beat scheduler configuration - UNIFIED CONFIGURATION
    beat_schedule={
        # Backup sync pending jobs every X minutes (from settings)
        "backup-sync-pending-jobs": {
            "task": "sync_pending_jobs_task",
            "schedule": float(settings.CELERY_SYNC_PENDING_JOBS_INTERVAL_SECONDS),
            "options": {"queue": "sync"},
        },
        # Poll for updates every X minutes (from settings)
        "poll-job-updates": {
            "task": "poll_synced_jobs_task",
            "schedule": float(settings.CELERY_POLL_JOB_UPDATES_INTERVAL_SECONDS),
            "options": {"queue": "poll"},
        },
        # Retry failed jobs every X minutes (from settings)
        "retry-failed-jobs": {
            "task": "retry_failed_jobs_task",
            "schedule": float(settings.CELERY_RETRY_FAILED_JOBS_INTERVAL_SECONDS),
            "options": {"queue": "retry"},
        },
        # Cleanup outbox events every X hours (from settings)
        "cleanup-outbox-events": {
            "task": "cleanup_outbox_events_task",
            "schedule": crontab(
                minute=0,
                hour=f"*/{settings.CELERY_CLEANUP_OUTBOX_EVENTS_INTERVAL_HOURS}",
            ),
            "options": {"queue": "maintenance"},
        },
        # Cleanup orphaned routings daily at X AM (from settings)
        "cleanup-orphaned-routings": {
            "task": "cleanup_orphaned_routings_task",
            "schedule": crontab(
                minute=0, hour=settings.CELERY_CLEANUP_ORPHANED_ROUTINGS_HOUR
            ),
            "options": {"queue": "maintenance"},
        },
    },
    # Task time limits
    task_soft_time_limit=30,  # 30 seconds soft limit
    task_time_limit=60,  # 1 minute hard limit
    # Retry configuration
    task_acks_late=False,  # Acknowledge immediately for better performance
    task_reject_on_worker_lost=settings.CELERY_TASK_REJECT_ON_WORKER_LOST,
    # Monitoring and metrics
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Security - use environment variable or default
    security_key=os.getenv("SECRET_KEY", "default_secret_key"),
    security_certificate=None,
    security_cert_store=None,
    # Event loop and async configuration
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
    worker_redirect_stdouts_level="WARNING",
    # Memory and performance configuration
    worker_max_memory_per_child=200000,  # 200MB
    # Queue priority configuration
    task_queue_max_priority=10,
    worker_direct=True,  # Direct task execution
)

# Task annotations for specific tasks - UNIFIED CONFIGURATION
celery_app.conf.task_annotations = {
    "sync_job_task": {
        "rate_limit": settings.CELERY_SYNC_JOB_TASK_RATE_LIMIT,
        "time_limit": settings.CELERY_TASK_TIME_LIMIT,
        "soft_time_limit": settings.CELERY_TASK_SOFT_TIME_LIMIT,
        "priority": 1,  # Highest priority for immediate execution
        "queue": "default",
    },
    "sync_pending_jobs_task": {
        "rate_limit": settings.CELERY_SYNC_PENDING_JOBS_TASK_RATE_LIMIT,
        "time_limit": settings.CELERY_TASK_TIME_LIMIT,
        "soft_time_limit": settings.CELERY_TASK_SOFT_TIME_LIMIT,
        "priority": 5,  # Lower priority for backup tasks
    },
    "poll_synced_jobs_task": {
        "rate_limit": settings.CELERY_POLL_SYNCED_JOBS_TASK_RATE_LIMIT,
        "time_limit": settings.CELERY_TASK_TIME_LIMIT,
        "soft_time_limit": settings.CELERY_TASK_SOFT_TIME_LIMIT,
        "priority": 10,  # Lower priority for polling
    },
    "retry_failed_jobs_task": {
        "rate_limit": settings.CELERY_RETRY_FAILED_JOBS_TASK_RATE_LIMIT,
        "time_limit": settings.CELERY_TASK_TIME_LIMIT,
        "soft_time_limit": settings.CELERY_TASK_SOFT_TIME_LIMIT,
        "priority": 15,  # Lower priority for retry
    },
}

# Import tasks to ensure they are registered
celery_app.autodiscover_tasks(["src.background.tasks"])

# Debug: List registered tasks
print("=== REGISTERED CELERY TASKS ===")
for task_name in celery_app.tasks.keys():
    if task_name.startswith("src.background.tasks"):
        print(f"  ✓ {task_name}")
print("================================")

if __name__ == "__main__":
    celery_app.start()
