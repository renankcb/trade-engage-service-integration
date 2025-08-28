"""
Transactional Outbox Pattern implementation for atomic operations.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.config.logging import get_logger

logger = get_logger(__name__)


class OutboxEventType(str, Enum):
    """Types of outbox events."""
    JOB_SYNC = "job_sync"
    JOB_STATUS_UPDATE = "job_status_update"
    COMPANY_SYNC = "company_sync"
    PROVIDER_SYNC = "provider_sync"


class OutboxEventStatus(str, Enum):
    """Status of outbox events."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OutboxEvent:
    """Outbox event for transactional operations."""
    id: UUID
    event_type: OutboxEventType
    aggregate_id: str  # ID of the main entity (e.g., job_id, company_id)
    event_data: Dict[str, Any]
    status: OutboxEventStatus = OutboxEventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TransactionalOutbox:
    """Transactional Outbox service for atomic operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger

    async def create_event(
        self,
        event_type: OutboxEventType,
        aggregate_id: str,
        event_data: Dict[str, Any],
        max_retries: int = 3
    ) -> OutboxEvent:
        """
        Create an outbox event within the current transaction.
        
        This method should be called within a database transaction to ensure
        atomicity between the main operation and the event creation.
        """
        event = OutboxEvent(
            id=uuid4(),
            event_type=event_type,
            aggregate_id=aggregate_id,
            event_data=event_data,
            max_retries=max_retries,
            created_at=datetime.utcnow()
        )
        
        # Insert event into outbox table
        await self._insert_event(event)
        
        self.logger.info(
            "Outbox event created",
            event_id=str(event.id),
            event_type=event.event_type.value,
            aggregate_id=event.aggregate_id
        )
        
        return event

    async def _insert_event(self, event: OutboxEvent) -> None:
        """Insert event into the outbox table."""
        stmt = text("""
            INSERT INTO outbox_events (
                id, event_type, aggregate_id, event_data, status, 
                retry_count, max_retries, created_at
            ) VALUES (
                :id, :event_type, :aggregate_id, :event_data, :status,
                :retry_count, :max_retries, :created_at
            )
        """)
        
        await self.db_session.execute(stmt, {
            "id": event.id,
            "event_type": event.event_type.value,
            "aggregate_id": event.aggregate_id,
            "event_data": json.dumps(event.event_data),
            "status": event.status.value,
            "retry_count": event.retry_count,
            "max_retries": event.retry_count,
            "created_at": event.created_at
        })

    async def mark_event_processing(self, event_id: UUID) -> bool:
        """Mark an event as processing to prevent duplicate processing."""
        stmt = text("""
            UPDATE outbox_events 
            SET status = :status, processed_at = :processed_at
            WHERE id = :event_id AND status = :pending_status
            RETURNING id
        """)
        
        result = await self.db_session.execute(stmt, {
            "event_id": event_id,
            "status": OutboxEventStatus.PROCESSING.value,
            "processed_at": datetime.utcnow(),
            "pending_status": OutboxEventStatus.PENDING.value
        })
        
        return result.rowcount > 0

    async def mark_event_completed(self, event_id: UUID) -> None:
        """Mark an event as completed."""
        stmt = text("""
            UPDATE outbox_events 
            SET status = :status, processed_at = :processed_at
            WHERE id = :event_id
        """)
        
        await self.db_session.execute(stmt, {
            "event_id": event_id,
            "status": OutboxEventStatus.COMPLETED.value,
            "processed_at": datetime.utcnow()
        })

    async def mark_event_failed(self, event_id: UUID, error_message: str) -> None:
        """Mark an event as failed with error message."""
        stmt = text("""
            UPDATE outbox_events 
            SET status = :status, error_message = :error_message, 
                retry_count = retry_count + 1, processed_at = :processed_at
            WHERE id = :event_id
        """)
        
        await self.db_session.execute(stmt, {
            "event_id": event_id,
            "status": OutboxEventStatus.FAILED.value,
            "error_message": error_message,
            "processed_at": datetime.utcnow()
        })

    async def get_pending_events(
        self, 
        event_type: Optional[OutboxEventType] = None,
        limit: int = 100
    ) -> List[OutboxEvent]:
        """Get pending events for processing."""
        where_clause = "WHERE status = :pending_status"
        params = {"pending_status": OutboxEventStatus.PENDING.value}
        
        if event_type:
            where_clause += " AND event_type = :event_type"
            params["event_type"] = event_type.value
        
        stmt = text(f"""
            SELECT id, event_type, aggregate_id, event_data, status,
                   retry_count, max_retries, created_at, processed_at, error_message
            FROM outbox_events
            {where_clause}
            ORDER BY created_at ASC
            LIMIT :limit
        """)
        
        params["limit"] = limit
        result = await self.db_session.execute(stmt, params)
        
        events = []
        for row in result.fetchall():
            event = OutboxEvent(
                id=row[0],
                event_type=OutboxEventType(row[1]),
                aggregate_id=row[2],
                event_data=json.loads(row[3]),
                status=OutboxEventStatus(row[4]),
                retry_count=row[5],
                max_retries=row[6],
                created_at=row[7],
                processed_at=row[8],
                error_message=row[9]
            )
            events.append(event)
        
        return events

    async def cleanup_completed_events(self, days_old: int = 7) -> int:
        """Clean up completed events older than specified days."""
        stmt = text("""
            DELETE FROM outbox_events 
            WHERE status = :completed_status 
            AND created_at < NOW() - INTERVAL ':days_old days'
        """)
        
        result = await self.db_session.execute(stmt, {
            "completed_status": OutboxEventStatus.COMPLETED.value,
            "days_old": days_old
        })
        
        deleted_count = result.rowcount
        self.logger.info(
            "Cleaned up completed outbox events",
            deleted_count=deleted_count,
            days_old=days_old
        )
        
        return deleted_count
