"""
Job routing domain entity.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from src.domain.exceptions.sync_error import SyncStatusError
from src.domain.value_objects.sync_status import SyncStatus


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
    last_sync_attempt: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    claimed_at: Optional[datetime] = None  # When this routing was claimed for processing
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize timestamps."""
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()

    def can_sync(self) -> bool:
        """Check if job routing can be synced."""
        if self.sync_status == SyncStatus.COMPLETED:
            return False

        if self.sync_status == SyncStatus.FAILED:
            return self.should_retry()

        return self.sync_status == SyncStatus.PENDING

    def mark_sync_started(self) -> None:
        """Mark sync as started."""
        if not self.can_sync():
            raise SyncStatusError(
                str(self.sync_status), "pending or failed with retries available"
            )

        self.last_sync_attempt = datetime.utcnow()
        self.total_sync_attempts += 1
        self.updated_at = datetime.utcnow()

    def mark_sync_success(self, external_id: str) -> None:
        """Mark sync as successful."""
        if not external_id:
            raise ValueError("External ID is required for successful sync")

        self.external_id = external_id
        self.sync_status = SyncStatus.SYNCED
        self.last_synced_at = datetime.utcnow()
        self.error_message = None
        self.next_retry_at = None
        self.updated_at = datetime.utcnow()

    def mark_sync_failed(self, error_message: str) -> None:
        """Mark sync as failed and calculate next retry time."""
        self.sync_status = SyncStatus.FAILED
        self.retry_count += 1
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

        # Calculate next retry time with exponential backoff
        if self.retry_count <= 3:
            backoff_minutes = 2 ** (self.retry_count - 1) * 5  # 5, 10, 20 minutes
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
        else:
            self.next_retry_at = None

    def mark_completed(self) -> None:
        """Mark job as completed in external system."""
        if self.sync_status != SyncStatus.SYNCED:
            raise SyncStatusError(str(self.sync_status), "synced")

        self.sync_status = SyncStatus.COMPLETED
        self.last_synced_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def should_retry(self) -> bool:
        """Check if sync should be retried."""
        if self.retry_count >= 3:
            return False

        if not self.next_retry_at:
            return False

        return datetime.utcnow() >= self.next_retry_at

    def reset_for_retry(self) -> None:
        """Reset routing for retry."""
        if not self.should_retry():
            raise SyncStatusError(
                str(self.sync_status), "failed with retries available"
            )

        self.sync_status = SyncStatus.PENDING
        self.error_message = None
        self.updated_at = datetime.utcnow()

    def is_duplicate_lead(self, external_id: str) -> bool:
        """Check if this routing represents a duplicate lead."""
        return self.external_id == external_id and self.sync_status in [
            SyncStatus.SYNCED,
            SyncStatus.COMPLETED,
        ]
