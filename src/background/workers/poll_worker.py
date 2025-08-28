"""
Poll Worker for checking job status updates from external providers.
"""

import asyncio
from typing import List, Optional
from uuid import UUID
import structlog

from src.application.use_cases.poll_updates import PollUpdatesUseCase
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
from src.application.services.rate_limiter import RateLimiter
from src.application.services.retry_handler import RetryHandler
from src.config.logging import get_logger

logger = get_logger(__name__)


class PollWorker:
    """Worker for polling job status updates from external providers."""

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
        
        # Initialize use case
        self.poll_use_case = PollUpdatesUseCase(
            job_routing_repo=self.job_routing_repo,
            company_repo=self.company_repo,
            job_repo=self.job_repo,
            provider_manager=self.provider_manager,
        )
        
        # Statistics
        self.poll_count = 0
        self.updates_found = 0
        self.completed_jobs = 0
        self.error_count = 0
        self.is_running = False

    async def poll_job_updates(self, limit: int = 50) -> dict:
        """
        Poll for job status updates from external providers.
        
        Args:
            limit: Maximum number of job routings to check
            
        Returns:
            Dictionary with polling results
        """
        try:
            self.logger.info(
                "Starting job status polling",
                limit=limit
            )
            
            # Check rate limiting for polling operations
            rate_limit_key = "poll:job_updates"
            if not await self.rate_limiter.check_and_increment(
                rate_limit_key,
                max_requests=30,  # 30 polls per minute
                window_seconds=60
            ):
                self.logger.warning("Rate limit exceeded for job polling")
                return {
                    "status": "rate_limited",
                    "message": "Polling rate limit exceeded"
                }
            
            # Execute polling with retry logic
            result = await self.retry_handler.execute_with_retry(
                lambda: self.poll_use_case.execute(),
                max_retries=2,
                base_delay=5.0,
                operation_key="poll_job_updates"
            )
            
            self.poll_count += 1
            
            if result:
                self.updates_found += result.updated
                self.completed_jobs += result.completed
                
                self.logger.info(
                    "Job status polling completed successfully",
                    total_polled=result.total_polled,
                    updates_found=result.updated,
                    completed_jobs=result.completed
                )
                
                return {
                    "status": "success",
                    "total_polled": result.total_polled,
                    "updates_found": result.updated,
                    "completed_jobs": result.completed
                }
            else:
                self.error_count += 1
                self.logger.error("Job status polling failed")
                return {
                    "status": "failed",
                    "message": "Polling operation failed"
                }
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(
                "Job status polling exception",
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "error": str(e)
            }

    async def poll_specific_job(self, job_id: UUID) -> dict:
        """
        Poll for updates on a specific job.
        
        Args:
            job_id: ID of the job to poll
            
        Returns:
            Dictionary with polling results
        """
        try:
            self.logger.info(
                "Polling specific job for updates",
                job_id=str(job_id)
            )
            
            # Get all routings for this job
            job_routings = await self.job_routing_repo.find_by_job_id(job_id)
            
            if not job_routings:
                return {
                    "status": "not_found",
                    "message": f"No routings found for job {job_id}"
                }
            
            # Check each routing for updates
            updates_found = 0
            for routing in job_routings:
                if routing.sync_status.value in ["synced", "processing"]:
                    try:
                        # Poll this specific routing
                        company = await self.company_repo.get_by_id(routing.company_id_received)
                        if company:
                            provider = self.provider_manager.get_provider(company.provider_type)
                            
                            # Check if provider supports status checking
                            if hasattr(provider, 'get_job_status'):
                                status_result = await provider.get_job_status(
                                    external_id=routing.external_id,
                                    company_config=company.provider_config
                                )
                                
                                if status_result and status_result.status != routing.sync_status.value:
                                    # Update routing status
                                    routing.sync_status = status_result.status
                                    if status_result.external_data:
                                        routing.external_data = status_result.external_data
                                    
                                    await self.job_routing_repo.update(routing)
                                    updates_found += 1
                                    
                                    self.logger.info(
                                        "Job routing status updated",
                                        routing_id=str(routing.id),
                                        old_status=routing.sync_status.value,
                                        new_status=status_result.status
                                    )
                    
                    except Exception as e:
                        self.logger.error(
                            "Error polling specific routing",
                            routing_id=str(routing.id),
                            error=str(e)
                        )
            
            return {
                "status": "success",
                "job_id": str(job_id),
                "routings_checked": len(job_routings),
                "updates_found": updates_found
            }
            
        except Exception as e:
            self.logger.error(
                "Error polling specific job",
                job_id=str(job_id),
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "error": str(e)
            }

    async def start_continuous_polling(self, interval_seconds: int = 300):  # 5 minutes
        """
        Start continuous polling for job updates.
        
        Args:
            interval_seconds: Interval between polling cycles
        """
        self.logger.info(
            "Starting continuous job status polling",
            interval_seconds=interval_seconds
        )
        
        self.is_running = True
        
        while self.is_running:
            try:
                await self.poll_job_updates(limit=100)
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(
                    "Error in continuous polling",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(interval_seconds)
    
    def stop_continuous_polling(self):
        """Stop continuous polling."""
        self.logger.info("Stopping continuous job status polling")
        self.is_running = False
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "is_running": self.is_running,
            "total_polls": self.poll_count,
            "total_updates_found": self.updates_found,
            "total_completed_jobs": self.completed_jobs,
            "total_errors": self.error_count,
            "success_rate": (self.poll_count - self.error_count) / self.poll_count if self.poll_count > 0 else 0
        }
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for polling operations."""
        return {
            "poll_operations": self.retry_handler.get_circuit_breaker_status("poll_job_updates"),
            "rate_limiter": "active"
        }
