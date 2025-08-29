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

    def __init__(self, outbox_service: TransactionalOutbox):
        self.outbox_service = outbox_service
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.retry_count = 0  # Track successful retries
        self._queued_routings = set()  # Track queued routings to prevent duplicates

    async def process_pending_events(self, batch_size: int = 50) -> int:
        """Process pending outbox events."""
        try:
            logger.info("Starting outbox event processing", batch_size=batch_size)

            # Get pending events
            pending_events = await self.outbox_service.get_pending_events(
                limit=batch_size
            )

            # Get failed events that can be retried (limited to avoid overwhelming)
            retry_limit = max(1, batch_size // 4)  # 25% of batch for retries
            failed_events = await self.outbox_service.get_failed_events_for_retry(
                limit=retry_limit
            )

            # Combine events: pending first, then retries
            all_events = pending_events + failed_events
            total_events = len(all_events)

            if not all_events:
                logger.info("No pending or retryable events found")
                return 0

            logger.info(
                "Retrieved events for processing",
                pending_count=len(pending_events),
                retry_count=len(failed_events),
                total_count=total_events,
            )

            # Process each event
            processed_count = 0
            error_count = 0
            retry_count = 0

            for event in all_events:
                try:
                    # Check if this is a retry
                    is_retry = event.status.value == "failed"

                    if is_retry:
                        # Check if we should retry based on retry count and timing
                        if not self._should_retry_event(event):
                            logger.info(
                                "Skipping retry - event has exceeded retry limits",
                                event_id=str(event.id),
                                retry_count=event.retry_count,
                                max_retries=event.max_retries,
                            )
                            continue

                        # Reset event to pending for retry
                        reset_success = await self.outbox_service.reset_event_for_retry(
                            event.id
                        )
                        if not reset_success:
                            logger.warning(
                                "Failed to reset event for retry",
                                event_id=str(event.id),
                            )
                            continue
                        retry_count += 1
                        self.retry_count += 1  # Increment successful retry counter

                    # Mark event as processing
                    await self.outbox_service.mark_event_processing(event.id)

                    # Process the event
                    success = await self._process_event(event)

                    if success:
                        await self.outbox_service.mark_event_completed(event.id)
                        processed_count += 1
                        self.processed_count += 1
                    else:
                        await self.outbox_service.mark_event_failed(
                            event.id, "Processing failed"
                        )
                        error_count += 1
                        self.error_count += 1

                except Exception as e:
                    logger.error(
                        "Error processing outbox event",
                        event_id=str(event.id),
                        is_retry=is_retry,
                        error=str(e),
                        exc_info=True,
                    )
                    error_count += 1
                    self.error_count += 1
                    await self.outbox_service.mark_event_failed(event.id, str(e))

            logger.info(
                "Outbox event processing completed",
                total_events=total_events,
                pending_events=len(pending_events),
                retry_events=len(failed_events),
                processed_count=processed_count,
                error_count=error_count,
                retry_count=retry_count,
                total_processed=self.processed_count,
                total_errors=self.error_count,
            )

            return processed_count

        except Exception as e:
            logger.error(
                "Error in outbox event processing", error=str(e), exc_info=True
            )
            return 0

    def _should_retry_event(self, event) -> bool:
        """
        Determine if an event should be retried based on retry count and timing.

        Implements exponential backoff:
        - 1st retry: after 5 minutes
        - 2nd retry: after 15 minutes
        - 3rd retry: after 45 minutes
        """
        if event.retry_count >= event.max_retries:
            return False

        if not event.processed_at:
            return True

        # Calculate delay based on retry count (exponential backoff)
        base_delay_minutes = 5
        delay_minutes = base_delay_minutes * (3**event.retry_count)

        # Check if enough time has passed since last attempt
        from datetime import datetime, timedelta, timezone

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=delay_minutes)

        return event.processed_at < cutoff_time

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
                logger.warning(
                    "Unknown event type",
                    event_id=str(event.id),
                    event_type=event.event_type.value,
                )
                return False

        except Exception as e:
            logger.error(
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
                logger.error(
                    "Missing routing_id in job sync event", event_id=str(event.id)
                )
                return False

            # Check if we already processed this routing recently to prevent duplicates
            if self._is_routing_already_queued(routing_id):
                logger.info(
                    "Job sync task already queued for this routing - skipping duplicate",
                    event_id=str(event.id),
                    routing_id=routing_id,
                )
                return True  # Mark as processed to avoid reprocessing

            # Import here to avoid circular imports
            from src.background.tasks.sync_jobs import sync_job_task

            # Enqueue Celery task for job sync
            logger.info(
                "Enqueueing sync_job_task",
                event_id=str(event.id),
                routing_id=routing_id,
                queue="default",
            )

            result = sync_job_task.delay(routing_id)

            logger.info(
                "sync_job_task enqueued successfully",
                event_id=str(event.id),
                routing_id=routing_id,
                task_id=result.id,
                task_status=result.status,
            )

            # Mark this routing as queued to prevent duplicates
            self._mark_routing_as_queued(routing_id)

            return True

        except Exception as e:
            logger.error(
                "Failed to process job sync event", event_id=str(event.id), error=str(e)
            )
            return False

    async def _process_job_status_update_event(self, event: OutboxEvent) -> bool:
        """Process job status update event."""
        # TODO: Implement job status update processing
        logger.info(
            "Job status update event processing not yet implemented",
            event_id=str(event.id),
        )
        return True

    async def _process_company_sync_event(self, event: OutboxEvent) -> bool:
        """Process company sync event."""
        # TODO: Implement company sync processing
        logger.info(
            "Company sync event processing not yet implemented", event_id=str(event.id)
        )
        return True

    async def _process_provider_sync_event(self, event: OutboxEvent) -> bool:
        """Process provider sync event."""
        # TODO: Implement provider sync processing
        logger.info(
            "Provider sync event processing not yet implemented", event_id=str(event.id)
        )
        return True

    async def start_continuous_processing(self, interval_seconds: int = 30):
        """
        Start continuous processing of outbox events.

        Args:
            interval_seconds: Interval between processing batches
        """
        logger.info(
            "Starting continuous outbox event processing",
            interval_seconds=interval_seconds,
        )

        self.is_running = True

        while self.is_running:
            try:
                await self.process_pending_events()
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(
                    "Error in continuous outbox processing", error=str(e), exc_info=True
                )
                await asyncio.sleep(interval_seconds)

    def stop_continuous_processing(self):
        """Stop continuous processing."""
        logger.info("Stopping continuous outbox event processing")
        self.is_running = False

    def get_stats(self) -> dict:
        """Get worker statistics."""
        total_operations = self.processed_count + self.error_count
        return {
            "is_running": self.is_running,
            "total_processed": self.processed_count,
            "total_errors": self.error_count,
            "total_retries": self.retry_count,
            "success_rate": (self.processed_count / total_operations)
            if total_operations > 0
            else 0,
            "retry_rate": (self.retry_count / total_operations)
            if total_operations > 0
            else 0,
        }

    def _is_routing_already_queued(self, routing_id: str) -> bool:
        """Check if a routing is already queued for processing."""
        return routing_id in self._queued_routings

    def _mark_routing_as_queued(self, routing_id: str) -> None:
        """Mark a routing as queued to prevent duplicates."""
        self._queued_routings.add(routing_id)

        # Clean up after a delay to prevent memory leaks
        # This routing will be removed from the set after 5 minutes
        asyncio.create_task(self._cleanup_queued_routing(routing_id, delay_seconds=300))

    async def _cleanup_queued_routing(
        self, routing_id: str, delay_seconds: int
    ) -> None:
        """Remove a routing from the queued set after a delay."""
        try:
            await asyncio.sleep(delay_seconds)
            self._queued_routings.discard(routing_id)
            logger.debug(
                "Cleaned up queued routing from tracking set",
                routing_id=routing_id,
                remaining_count=len(self._queued_routings),
            )
        except Exception as e:
            logger.error(
                "Error during cleanup of queued routing",
                routing_id=routing_id,
                error=str(e),
            )
            # Ensure cleanup happens even if there's an error
            self._queued_routings.discard(routing_id)
