"""
Outbox Worker for processing transactional outbox events.
"""

import asyncio
from typing import List

import structlog

from src.application.services.transactional_outbox import (
    OutboxEvent,
    OutboxEventType,
    TransactionalOutbox,
)
from src.config.logging import get_logger

logger = get_logger(__name__)


class OutboxWorker:
    """Worker for processing outbox events."""

    def __init__(self, outbox: TransactionalOutbox):
        self.outbox = outbox
        self.logger = logger
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0

    async def process_pending_events(self, batch_size: int = 50) -> int:
        """
        Process pending outbox events.

        Args:
            batch_size: Maximum number of events to process in this batch

        Returns:
            Number of events processed
        """
        self.logger.info("Starting outbox event processing", batch_size=batch_size)

        # Get pending events
        pending_events = await self.outbox.get_pending_events(limit=batch_size)

        if not pending_events:
            self.logger.info("No pending outbox events found")
            return 0

        processed_count = 0
        error_count = 0

        for event in pending_events:
            try:
                # Mark event as processing (atomic operation)
                if not await self.outbox.mark_event_processing(event.id):
                    self.logger.warning(
                        "Event already being processed or not found",
                        event_id=str(event.id),
                    )
                    continue

                # Process event based on type
                success = await self._process_event(event)

                if success:
                    await self.outbox.mark_event_completed(event.id)
                    processed_count += 1
                    self.processed_count += 1

                    self.logger.info(
                        "Outbox event processed successfully",
                        event_id=str(event.id),
                        event_type=event.event_type.value,
                        aggregate_id=event.aggregate_id,
                    )
                else:
                    await self.outbox.mark_event_failed(
                        event.id, "Event processing failed"
                    )
                    error_count += 1
                    self.error_count += 1

                    self.logger.error(
                        "Outbox event processing failed",
                        event_id=str(event.id),
                        event_type=event.event_type.value,
                        aggregate_id=event.aggregate_id,
                    )

            except Exception as e:
                error_count += 1
                self.error_count += 1

                self.logger.error(
                    "Error processing outbox event",
                    event_id=str(event.id),
                    error=str(e),
                    exc_info=True,
                )

                await self.outbox.mark_event_failed(event.id, str(e))

        self.logger.info(
            "Outbox event processing completed",
            total_events=len(pending_events),
            processed_count=processed_count,
            error_count=error_count,
            total_processed=self.processed_count,
            total_errors=self.error_count,
        )

        return processed_count

    async def _process_event(self, event: OutboxEvent) -> bool:
        """
        Process a specific outbox event.

        Args:
            event: The outbox event to process

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            if event.event_type == OutboxEventType.JOB_SYNC:
                return await self._process_job_sync_event(event)
            elif event.event_type == OutboxEventType.JOB_STATUS_UPDATE:
                return await self._process_job_status_update_event(event)
            elif event.event_type == OutboxEventType.COMPANY_SYNC:
                return await self._process_company_sync_event(event)
            elif event.event_type == OutboxEventType.PROVIDER_SYNC:
                return await self._process_provider_sync_event(event)
            else:
                self.logger.warning(
                    "Unknown event type",
                    event_id=str(event.id),
                    event_type=event.event_type.value,
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error processing event",
                event_id=str(event.id),
                event_type=event.event_type.value,
                error=str(e),
            )
            return False

    async def _process_job_sync_event(self, event: OutboxEvent) -> bool:
        """Process job sync event by enqueueing Celery task."""
        try:
            routing_id = event.event_data.get("routing_id")
            if not routing_id:
                self.logger.error(
                    "Missing routing_id in job sync event", event_id=str(event.id)
                )
                return False

            # Import here to avoid circular imports
            from src.background.tasks.sync_jobs import sync_job_task

            # Enqueue Celery task for job sync
            sync_job_task.delay(routing_id)

            self.logger.info(
                "Job sync task enqueued from outbox event",
                event_id=str(event.id),
                routing_id=routing_id,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to process job sync event", event_id=str(event.id), error=str(e)
            )
            return False

    async def _process_job_status_update_event(self, event: OutboxEvent) -> bool:
        """Process job status update event."""
        # TODO: Implement job status update processing
        self.logger.info(
            "Job status update event processing not yet implemented",
            event_id=str(event.id),
        )
        return True

    async def _process_company_sync_event(self, event: OutboxEvent) -> bool:
        """Process company sync event."""
        # TODO: Implement company sync processing
        self.logger.info(
            "Company sync event processing not yet implemented", event_id=str(event.id)
        )
        return True

    async def _process_provider_sync_event(self, event: OutboxEvent) -> bool:
        """Process provider sync event."""
        # TODO: Implement provider sync processing
        self.logger.info(
            "Provider sync event processing not yet implemented", event_id=str(event.id)
        )
        return True

    async def start_continuous_processing(self, interval_seconds: int = 30):
        """
        Start continuous processing of outbox events.

        Args:
            interval_seconds: Interval between processing batches
        """
        self.logger.info(
            "Starting continuous outbox event processing",
            interval_seconds=interval_seconds,
        )

        self.is_running = True

        while self.is_running:
            try:
                await self.process_pending_events()
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                self.logger.error(
                    "Error in continuous outbox processing", error=str(e), exc_info=True
                )
                await asyncio.sleep(interval_seconds)

    def stop_continuous_processing(self):
        """Stop continuous processing."""
        self.logger.info("Stopping continuous outbox event processing")
        self.is_running = False

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "is_running": self.is_running,
            "total_processed": self.processed_count,
            "total_errors": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
            )
            if (self.processed_count + self.error_count) > 0
            else 0,
        }
