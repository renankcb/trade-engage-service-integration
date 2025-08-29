"""
Application layer package.

This package contains use cases, services, and interfaces that implement
the business logic of the application.
"""

from .interfaces.providers import (
    CreateLeadRequest,
    CreateLeadResponse,
    ProviderInterface,
)
from .interfaces.repositories import (
    CompanyRepositoryInterface,
    JobRepositoryInterface,
    JobRoutingRepositoryInterface,
)
from .services.data_transformer import DataTransformer
from .services.provider_manager import ProviderManager
from .services.retry_handler import RetryHandler
from .services.transaction_service import TransactionService
from .services.transactional_outbox import TransactionalOutbox
from .use_cases.poll_updates import PollUpdatesUseCase
from .use_cases.sync_job import SyncJobUseCase

__all__ = [
    # Interfaces
    "ProviderInterface",
    "CreateLeadRequest",
    "CreateLeadResponse",
    "GetJobStatusRequest",
    "GetJobStatusResponse",
    "CompanyRepositoryInterface",
    "JobRepositoryInterface",
    "JobRoutingRepositoryInterface",
    "TransactionalOutbox",
    # Services
    "DataTransformer",
    "ProviderManager",
    "RetryHandler",
    "TransactionService",
    "TransactionalOutbox",
    # Use Cases
    "PollUpdatesUseCase",
    "SyncJobUseCase",
]
