"""
Sync failed domain event.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class SyncFailed:
    """Event raised when a sync operation fails."""
    
    sync_id: UUID
    provider_type: str
    failed_at: datetime
    error_message: str
    error_code: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
