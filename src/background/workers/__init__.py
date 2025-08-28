"""
Worker management and coordination.
"""

from typing import Dict, Any
import asyncio
import logging

from src.config.logging import get_logger
from src.background.workers.outbox_worker import OutboxWorker
from src.background.workers.sync_worker import SyncWorker
from src.background.workers.poll_worker import PollWorker

logger = get_logger(__name__)


class WorkerManager:
    """Manages and coordinates all background workers."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.logger = logger
        
        # Initialize workers
        self.outbox_worker = OutboxWorker(db_session)
        self.sync_worker = SyncWorker(db_session)
        self.poll_worker = PollWorker(db_session)
        
        # Worker tasks
        self.worker_tasks = {}
        self.is_running = False
    
    async def start_all_workers(self):
        """Start all background workers."""
        try:
            self.logger.info("Starting all background workers")
            
            # Start outbox worker (processes every 30 seconds)
            outbox_task = asyncio.create_task(
                self.outbox_worker.start_continuous_processing(interval_seconds=30)
            )
            self.worker_tasks["outbox"] = outbox_task
            
            # Start sync worker (processes every 60 seconds)
            sync_task = asyncio.create_task(
                self.sync_worker.start_continuous_sync(interval_seconds=60)
            )
            self.worker_tasks["sync"] = sync_task
            
            # Start poll worker (processes every 5 minutes)
            poll_task = asyncio.create_task(
                self.poll_worker.start_continuous_polling(interval_seconds=300)
            )
            self.worker_tasks["poll"] = poll_task
            
            self.is_running = True
            
            self.logger.info("All background workers started successfully")
            
        except Exception as e:
            self.logger.error(
                "Error starting background workers",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def stop_all_workers(self):
        """Stop all background workers."""
        try:
            self.logger.info("Stopping all background workers")
            
            # Stop workers
            self.outbox_worker.stop_continuous_processing()
            self.sync_worker.stop_continuous_sync()
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
                "Error stopping background workers",
                error=str(e),
                exc_info=True
            )
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics from all workers."""
        return {
            "manager": {
                "is_running": self.is_running,
                "active_workers": len(self.worker_tasks)
            },
            "outbox_worker": self.outbox_worker.get_stats(),
            "sync_worker": self.sync_worker.get_stats(),
            "poll_worker": self.poll_worker.get_stats()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all workers."""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "workers": {
                "outbox": {
                    "status": "running" if self.outbox_worker.is_running else "stopped",
                    "stats": self.outbox_worker.get_stats()
                },
                "sync": {
                    "status": "running" if self.sync_worker.is_running else "stopped",
                    "stats": self.sync_worker.get_stats()
                },
                "poll": {
                    "status": "running" if self.poll_worker.is_running else "stopped",
                    "stats": self.poll_worker.get_stats()
                }
            },
            "circuit_breakers": {
                "sync": self.sync_worker.get_circuit_breaker_status(),
                "poll": self.poll_worker.get_circuit_breaker_status()
            }
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
                outbox_task = asyncio.create_task(
                    self.outbox_worker.start_continuous_processing(interval_seconds=30)
                )
                self.worker_tasks["outbox"] = outbox_task
                
            elif worker_name == "sync":
                # Stop current task
                if "sync" in self.worker_tasks:
                    self.worker_tasks["sync"].cancel()
                
                # Start new task
                sync_task = asyncio.create_task(
                    self.sync_worker.start_continuous_sync(interval_seconds=60)
                )
                self.worker_tasks["sync"] = sync_task
                
            elif worker_name == "poll":
                # Stop current task
                if "poll" in self.worker_tasks:
                    self.worker_tasks["poll"].cancel()
                
                # Start new task
                poll_task = asyncio.create_task(
                    self.poll_worker.start_continuous_polling(interval_seconds=300)
                )
                self.worker_tasks["poll"] = poll_task
                
            else:
                raise ValueError(f"Unknown worker: {worker_name}")
            
            self.logger.info(f"Worker {worker_name} restarted successfully")
            
        except Exception as e:
            self.logger.error(
                f"Error restarting worker {worker_name}",
                error=str(e),
                exc_info=True
            )
            raise
