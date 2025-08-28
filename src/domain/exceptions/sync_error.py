"""
Sync-related domain exceptions.
"""


class SyncError(Exception):
    """Base exception for sync-related errors."""

    pass


class SyncRetryExceededError(SyncError):
    """Raised when maximum retry attempts are exceeded."""

    def __init__(self, job_routing_id: str, max_attempts: int):
        self.job_routing_id = job_routing_id
        self.max_attempts = max_attempts
        super().__init__(
            f"Sync retry exceeded for job routing {job_routing_id} after {max_attempts} attempts"
        )


class SyncStatusError(SyncError):
    """Raised when sync status is invalid for operation."""

    def __init__(self, current_status: str, required_status: str):
        self.current_status = current_status
        self.required_status = required_status
        super().__init__(
            f"Invalid sync status '{current_status}', expected '{required_status}'"
        )
