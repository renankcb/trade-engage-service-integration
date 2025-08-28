"""
Sync completed domain event.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class SyncCompleted:
    """Event raised when a sync operation completes successfully."""
    
    sync_id: UUID
    provider_type: str
    completed_at: datetime
    records_processed: int
    records_synced: int
    metadata: Optional[Dict[str, Any]] = None
