"""
Worker management and coordination.
"""

import asyncio
import logging
from typing import Any, Dict

from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class WorkerManager:
    """Manages and coordinates all background workers."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.logger = logger

        self.outbox_worker = None
        self.poll_worker = None

        # Worker tasks
        self.worker_tasks = {}
        self.is_running = False

    def _get_outbox_worker(self):
        """Lazy initialization of outbox worker."""
        if self.outbox_worker is None:
            from src.background.workers.outbox_worker import OutboxWorker

            # Create a new session for the outbox worker
            from src.config.database import async_session_factory
            from src.infrastructure.database.repositories.transactional_outbox_repository import (
                TransactionalOutbox,
            )

            outbox_service = TransactionalOutbox(async_session_factory())
            self.outbox_worker = OutboxWorker(outbox_service)
        return self.outbox_worker

    def _get_poll_worker(self):
        """Lazy initialization of poll worker."""
        if self.poll_worker is None:
            from src.background.workers.poll_worker import PollWorker

            # Create a new session for the poll worker
            from src.config.database import async_session_factory

            self.poll_worker = PollWorker(async_session_factory())
        return self.poll_worker

    async def start_all_workers(self):
        """Start all background workers."""
        try:
            self.logger.info("Starting all background workers")

            # Start outbox worker (processes every X seconds from settings)
            outbox_worker = self._get_outbox_worker()
            outbox_task = asyncio.create_task(
                outbox_worker.start_continuous_processing(
                    interval_seconds=settings.BACKGROUND_WORKER_OUTBOX_INTERVAL_SECONDS
                )
            )
            self.worker_tasks["outbox"] = outbox_task

            # NOTE: SyncWorker no longer runs continuously
            # It only executes tasks enqueued by OutboxWorker via Celery
            # This prevents duplication and ensures proper task flow
            self.logger.info(
                "SyncWorker configured for task execution only (no continuous processing)"
            )

            # Start poll worker (processes every X seconds from settings)
            poll_worker = self._get_poll_worker()
            poll_task = asyncio.create_task(
                poll_worker.start_continuous_polling(
                    interval_seconds=settings.BACKGROUND_WORKER_POLL_INTERVAL_SECONDS
                )
            )
            self.worker_tasks["poll"] = poll_task

            self.is_running = True

            self.logger.info("All background workers started successfully")

        except Exception as e:
            self.logger.error(
                "Error starting background workers", error=str(e), exc_info=True
            )
            raise

    async def stop_all_workers(self):
        """Stop all background workers."""
        try:
            self.logger.info("Stopping all background workers")

            # Stop workers
            if self.outbox_worker:
                self.outbox_worker.stop_continuous_processing()
            if self.poll_worker:
                self.poll_worker.stop_continuous_polling()

            # Cancel tasks
            for task_name, task in self.worker_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            self.worker_tasks.clear()
            self.is_running = False

            self.logger.info("All background workers stopped successfully")

        except Exception as e:
            self.logger.error(
                "Error stopping background workers", error=str(e), exc_info=True
            )

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics from all workers."""
        return {
            "manager": {
                "is_running": self.is_running,
                "active_workers": len(self.worker_tasks),
            },
            "outbox_worker": self._get_outbox_worker().get_stats()
            if self.outbox_worker
            else {},
            "poll_worker": self._get_poll_worker().get_stats()
            if self.poll_worker
            else {},
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all workers."""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "workers": {
                "outbox": {
                    "status": "running"
                    if self.outbox_worker and self.outbox_worker.is_running
                    else "stopped",
                    "stats": self._get_outbox_worker().get_stats()
                    if self.outbox_worker
                    else {},
                },
                "poll": {
                    "status": "running"
                    if self.poll_worker and self.poll_worker.is_running
                    else "stopped",
                    "stats": self._get_poll_worker().get_stats()
                    if self.poll_worker
                    else {},
                },
            },
            "circuit_breakers": {
                "poll": self._get_poll_worker().get_circuit_breaker_status()
                if self.poll_worker
                else {},
            },
        }

    async def restart_worker(self, worker_name: str):
        """Restart a specific worker."""
        try:
            self.logger.info(f"Restarting worker: {worker_name}")

            if worker_name == "outbox":
                # Stop current task
                if "outbox" in self.worker_tasks:
                    self.worker_tasks["outbox"].cancel()

                # Start new task
                outbox_worker = self._get_outbox_worker()
                outbox_task = asyncio.create_task(
                    outbox_worker.start_continuous_processing(interval_seconds=30)
                )
                self.worker_tasks["outbox"] = outbox_task

            elif worker_name == "poll":
                # Stop current task
                if "poll" in self.worker_tasks:
                    self.worker_tasks["poll"].cancel()

                # Start new task
                poll_worker = self._get_poll_worker()
                poll_task = asyncio.create_task(
                    poll_worker.start_continuous_polling(interval_seconds=300)
                )
                self.worker_tasks["poll"] = poll_task

            else:
                raise ValueError(f"Unknown worker: {worker_name}")

            self.logger.info(f"Worker {worker_name} restarted successfully")

        except Exception as e:
            self.logger.error(
                f"Error restarting worker {worker_name}", error=str(e), exc_info=True
            )
            raise
