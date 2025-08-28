"""
Sync status value object.
"""

from enum import Enum


class SyncStatus(str, Enum):
    """Job routing sync status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SYNCED = "synced"
    FAILED = "failed"
    COMPLETED = "completed"

    def can_retry(self) -> bool:
        """Check if status allows retry."""
        return self in [self.PENDING, self.FAILED]

    def is_final(self) -> bool:
        """Check if status is final (no more processing)."""
        return self in [self.COMPLETED]

    def is_active(self) -> bool:
        """Check if status requires active monitoring."""
        return self == self.SYNCED

    def can_be_claimed(self) -> bool:
        """Check if status allows claiming for processing."""
        return self in [self.PENDING, self.FAILED]
