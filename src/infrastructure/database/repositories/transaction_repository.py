"""
Transaction service for managing database transactions centrally.
"""

from typing import AsyncGenerator, Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class TransactionService:
    """Centralized transaction management service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logger

    async def execute_in_transaction(self, operation: Callable[[], Awaitable[T]]) -> T:
        """
        Execute an operation within a transaction.

        Args:
            operation: Async function to execute

        Returns:
            Result of the operation

        Raises:
            Exception: Any exception that occurs during execution
        """
        try:
            # Execute the operation
            result = await operation()

            # Commit the transaction
            await self.session.commit()

            self.logger.info("Transaction committed successfully")
            return result

        except Exception as e:
            # Rollback on any error
            await self.session.rollback()
            self.logger.error(
                "Transaction rolled back due to error", error=str(e), exc_info=True
            )
            raise

    async def commit(self) -> None:
        """Explicitly commit the current transaction."""
        await self.session.commit()
        self.logger.debug("Transaction committed")

    async def rollback(self) -> None:
        """Explicitly rollback the current transaction."""
        await self.session.rollback()
        self.logger.debug("Transaction rolled back")

    async def flush(self) -> None:
        """Flush pending changes to the database."""
        await self.session.flush()
        self.logger.debug("Changes flushed to database")
