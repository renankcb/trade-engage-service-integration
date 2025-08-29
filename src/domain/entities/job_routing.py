"""
Job routing entity for managing job synchronization with external providers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.config.logging import get_logger
from src.domain.exceptions.sync_error import SyncStatusError
from src.domain.value_objects.sync_status import SyncStatus

logger = get_logger(__name__)


@dataclass
class JobRouting:
    """Job routing domain entity."""

    job_id: UUID
    company_id_received: UUID
    id: UUID = field(default_factory=uuid4)
    external_id: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    retry_count: int = 0
    total_sync_attempts: int = 0
    last_synced_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    claimed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    revenue: Optional[float] = None

    def __post_init__(self):
        """Initialize timestamps."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc)

    def can_sync(self) -> bool:
        """Check if job routing can be synced."""
        if self.sync_status == SyncStatus.COMPLETED:
            return False

        if self.sync_status == SyncStatus.FAILED:
            return self.should_retry()

        # Allow PROCESSING status for retry scenarios
        if self.sync_status == SyncStatus.PROCESSING:
            # Check if this is a retry scenario (processing for too long)
            return self.is_stuck(older_than_minutes=10)  # Allow retry after 10 minutes

        return self.sync_status == SyncStatus.PENDING

    def mark_sync_started(self) -> None:
        """Mark sync as started."""
        if not self.can_sync():
            raise SyncStatusError(
                str(self.sync_status), "pending or failed with retries available"
            )

        self.total_sync_attempts += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_as_processing_by_backup(self) -> None:
        """Mark routing as being processed by backup task."""
        if not self.can_sync():
            raise SyncStatusError(
                str(self.sync_status), "pending or failed with retries available"
            )

        # Mark as processing to prevent other tasks from interfering
        self.sync_status = SyncStatus.PROCESSING
        self.total_sync_attempts += 1
        self.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Job routing marked as processing by backup task",
            routing_id=str(self.id),
            sync_attempt=self.total_sync_attempts,
        )

    def get_stuck_duration_minutes(self) -> int:
        """Get how long this routing has been stuck in minutes."""
        if not self.updated_at:
            return 0

        duration = datetime.now(timezone.utc) - self.updated_at
        return int(duration.total_seconds() / 60)

    def is_stuck(self, older_than_minutes: int = 5) -> bool:
        """Check if this routing is stuck (older than specified minutes)."""
        return self.get_stuck_duration_minutes() >= older_than_minutes

    def can_be_processed_by_backup(self, older_than_minutes: int = 5) -> bool:
        """Check if this routing can be processed by backup task."""
        return (
            self.can_sync()
            and self.is_stuck(older_than_minutes)
            and self.sync_status
            not in [SyncStatus.PROCESSING, SyncStatus.SYNCED, SyncStatus.COMPLETED]
        )

    def mark_sync_success(self, external_id: str) -> None:
        """Mark sync as successful."""
        if not external_id:
            raise ValueError("External ID is required for successful sync")

        self.external_id = external_id
        self.sync_status = SyncStatus.SYNCED
        self.last_synced_at = datetime.now(timezone.utc)
        self.error_message = None
        self.next_retry_at = None
        self.updated_at = datetime.now(timezone.utc)
        self.last_synced_at = datetime.now(timezone.utc)

    def mark_sync_failed(self, error_message: str) -> None:
        """Mark sync as failed and calculate next retry time."""
        self.sync_status = SyncStatus.FAILED
        self.retry_count += 1
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)

        # Calculate next retry time with exponential backoff
        if self.retry_count <= 3:
            backoff_minutes = 2 ** (self.retry_count - 1) * 5  # 5, 10, 20 minutes
            self.next_retry_at = datetime.now(timezone.utc) + timedelta(
                minutes=backoff_minutes
            )
        else:
            self.next_retry_at = None

    def mark_completed(self, revenue: Optional[float] = None) -> None:
        """Mark job as completed in external system."""
        if self.sync_status != SyncStatus.SYNCED:
            raise SyncStatusError(str(self.sync_status), "synced")

        self.sync_status = SyncStatus.COMPLETED
        self.last_synced_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.revenue = revenue

    def should_retry(self) -> bool:
        """Check if sync should be retried."""
        if self.retry_count >= 3:
            return False

        if not self.next_retry_at:
            return False

        return datetime.now(timezone.utc) >= self.next_retry_at

    def reset_for_retry(self) -> None:
        """Reset routing for retry."""
        if not self.should_retry():
            raise SyncStatusError(
                str(self.sync_status), "failed with retries available"
            )

        self.sync_status = SyncStatus.PENDING
        self.error_message = None
        self.updated_at = datetime.now(timezone.utc)

    def is_duplicate_lead(self, external_id: str) -> bool:
        """Check if this routing represents a duplicate lead."""
        return self.external_id == external_id and self.sync_status in [
            SyncStatus.SYNCED,
            SyncStatus.COMPLETED,
        ]
