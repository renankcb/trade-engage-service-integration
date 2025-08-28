"""
Job routed domain event.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class JobRouted:
    """Event raised when a job is routed to a company."""
    
    job_id: UUID
    company_id: UUID
    routed_at: datetime
    routing_reason: Optional[str] = None
    metadata: Optional[dict] = None
