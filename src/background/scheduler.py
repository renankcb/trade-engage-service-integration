"""
Celery Beat scheduler configuration.

NOTE: This file is now DEPRECATED. All scheduling configuration
has been moved to celery_app.py to avoid duplication.
"""

from src.background.celery_app import celery_app

# This file is kept for backward compatibility but no longer
# adds any periodic tasks. All scheduling is now handled in
# celery_app.py with unified configuration from settings.

# The following tasks are now scheduled directly in celery_app.py:
# - sync_pending_jobs_task
# - poll_synced_jobs_task
# - retry_failed_jobs_task
# - cleanup_outbox_events_task
# - cleanup_orphaned_routings_task

# Task routing and rate limiting are also configured in celery_app.py
# to avoid duplication and ensure consistency.
