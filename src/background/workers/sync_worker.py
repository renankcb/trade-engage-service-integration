"""
Sync Worker for processing job synchronization tasks.
"""

import asyncio
from typing import List, Optional
from uuid import UUID
import structlog

from src.application.use_cases.sync_job import SyncJobUseCase
from src.infrastructure.database.repositories.job_routing_repository import (
    JobRoutingRepository
)
from src.infrastructure.database.repositories.job_repository import (
    JobRepository
)
from src.infrastructure.database.repositories.company_repository import (
    CompanyRepository
)
from src.infrastructure.providers.factory import ProviderFactory
from src.application.services.provider_manager import ProviderManager
from src.application.services.data_transformer import DataTransformer
from src.application.services.rate_limiter import RateLimiter
from src.application.services.retry_handler import RetryHandler
from src.config.logging import get_logger

logger = get_logger(__name__)


class SyncWorker:
    """Worker for processing job synchronization tasks."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.logger = logger
        
        # Initialize repositories and services
        self.job_routing_repo = JobRoutingRepository(db_session)
        self.job_repo = JobRepository(db_session)
        self.company_repo = CompanyRepository(db_session)
        self.provider_factory = ProviderFactory()
        self.rate_limiter = RateLimiter()
        self.retry_handler = RetryHandler()
        
        # Initialize provider manager with rate limiter and retry handler
        self.provider_manager = ProviderManager(
            self.provider_factory,
            self.company_repo,
            self.rate_limiter,
            self.retry_handler
        )
        
        self.data_transformer = DataTransformer()
        
        # Initialize use case
        self.sync_use_case = SyncJobUseCase(
            job_routing_repo=self.job_routing_repo,
            job_repo=self.job_repo,
            company_repo=self.company_repo,
            provider_manager=self.provider_manager,
            data_transformer=self.data_transformer,
        )
        
        # Statistics
        self.sync_count = 0
        self.success_count = 0
        self.error_count = 0
        self.is_running = False

    async def sync_job_routing(self, routing_id: UUID) -> bool:
        """
        Sync a specific job routing.
        
        Args:
            routing_id: ID of the job routing to sync
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            self.logger.info(
                "Starting job routing sync",
                routing_id=str(routing_id)
            )
            
            # Check rate limiting for this company
            routing = await self.job_routing_repo.get_by_id(routing_id)
            if routing:
                company = await self.company_repo.get_by_id(routing.company_id_received)
                if company:
                    rate_limit_key = f"sync:{company.id}:{company.provider_type.value}"
                    
                    if not await self.rate_limiter.check_and_increment(
                        rate_limit_key, 
                        max_requests=50,  # 50 syncs per minute per company
                        window_seconds=60
                    ):
                        self.logger.warning(
                            "Rate limit exceeded for company sync",
                            company_id=str(company.id),
                            provider_type=company.provider_type.value
                        )
                        return False
            
            # Execute sync with retry logic
            result = await self.retry_handler.execute_with_retry(
                lambda: self.sync_use_case.execute(routing_id),
                max_retries=3,
                base_delay=2.0,
                operation_key=f"sync_job:{routing_id}"
            )
            
            self.sync_count += 1
            
            if result:
                self.success_count += 1
                self.logger.info(
                    "Job routing sync completed successfully",
                    routing_id=str(routing_id)
                )
                return True
            else:
                self.error_count += 1
                self.logger.error(
                    "Job routing sync failed",
                    routing_id=str(routing_id)
                )
                return False
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(
                "Job routing sync exception",
                routing_id=str(routing_id),
                error=str(e),
                exc_info=True
            )
            return False

    async def sync_pending_routings(self, limit: int = 10) -> int:
        """
        Sync multiple pending job routings.
        
        Args:
            limit: Maximum number of routings to sync
            
        Returns:
            Number of routings processed
        """
        try:
            self.logger.info(
                "Starting batch sync of pending routings",
                limit=limit
            )
            
            # Get pending routings using claim pattern
            pending_routings = await self.job_routing_repo.claim_pending_routings(limit=limit)
            
            if not pending_routings:
                self.logger.info("No pending routings available for sync")
                return 0
            
            self.logger.info(
                "Found pending routings to sync",
                count=len(pending_routings)
            )
            
            # Process each routing
            processed_count = 0
            for routing in pending_routings:
                try:
                    success = await self.sync_job_routing(routing.id)
                    if success:
                        processed_count += 1
                    
                    # Small delay between syncs to avoid overwhelming providers
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(
                        "Error syncing routing",
                        routing_id=str(routing.id),
                        error=str(e)
                    )
            
            self.logger.info(
                "Batch sync completed",
                total_routings=len(pending_routings),
                successful_syncs=processed_count,
                failed_syncs=len(pending_routings) - processed_count
            )
            
            return processed_count
            
        except Exception as e:
            self.logger.error(
                "Error in batch sync",
                error=str(e),
                exc_info=True
            )
            return 0

    async def start_continuous_sync(self, interval_seconds: int = 60):
        """
        Start continuous sync processing.
        
        Args:
            interval_seconds: Interval between sync batches
        """
        self.logger.info(
            "Starting continuous sync processing",
            interval_seconds=interval_seconds
        )
        
        self.is_running = True
        
        while self.is_running:
            try:
                await self.sync_pending_routings(limit=20)
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(
                    "Error in continuous sync processing",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(interval_seconds)
    
    def stop_continuous_sync(self):
        """Stop continuous sync processing."""
        self.logger.info("Stopping continuous sync processing")
        self.is_running = False
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "is_running": self.is_running,
            "total_syncs": self.sync_count,
            "successful_syncs": self.success_count,
            "failed_syncs": self.error_count,
            "success_rate": (self.success_count / self.sync_count) if self.sync_count > 0 else 0
        }
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for all operations."""
        return {
            "sync_operations": self.retry_handler.get_circuit_breaker_status("sync_job"),
            "rate_limiter": "active"  # Could be enhanced with Redis stats
        }
