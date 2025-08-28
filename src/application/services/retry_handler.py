"""
Retry Handler service for managing retry logic and circuit breaker patterns.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar
import random
import logging

from src.config.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryHandlerInterface:
    """Interface for retry handling operations."""
    
    async def execute_with_retry(
        self, 
        operation: Callable[[], Any], 
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Any:
        """Execute operation with retry logic."""
        raise NotImplementedError


class RetryHandler(RetryHandlerInterface):
    """Retry handler with exponential backoff and jitter."""
    
    def __init__(self):
        self.logger = logger
        self.circuit_breaker_state = {}  # key -> (state, last_failure, failure_count)
    
    async def execute_with_retry(
        self, 
        operation: Callable[[], Any], 
        max_retries: int = 3,
        base_delay: float = 1.0,
        operation_key: str = "default"
    ) -> Any:
        """
        Execute operation with retry logic and circuit breaker.
        
        Args:
            operation: Async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            operation_key: Key for circuit breaker tracking
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retries are exhausted
        """
        # Check circuit breaker first
        if self._is_circuit_open(operation_key):
            raise Exception(f"Circuit breaker is open for {operation_key}")
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                
                # Success - reset circuit breaker
                self._record_success(operation_key)
                return result
                
            except Exception as e:
                last_exception = e
                
                # Record failure for circuit breaker
                self._record_failure(operation_key, e)
                
                # If this was the last attempt, don't retry
                if attempt == max_retries:
                    self.logger.error(
                        "Operation failed after all retries",
                        operation_key=operation_key,
                        total_attempts=attempt + 1,
                        final_error=str(e)
                    )
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt, base_delay)
                
                self.logger.warning(
                    "Operation failed, retrying",
                    operation_key=operation_key,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    next_retry_in_seconds=delay
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception
    
    def _calculate_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate delay with exponential backoff and jitter."""
        # Exponential backoff: base_delay * 2^attempt
        exponential_delay = base_delay * (2 ** attempt)
        
        # Add jitter (±25% random variation)
        jitter = exponential_delay * 0.25
        jittered_delay = exponential_delay + random.uniform(-jitter, jitter)
        
        # Cap at 60 seconds
        return min(jittered_delay, 60.0)
    
    def _is_circuit_open(self, operation_key: str) -> bool:
        """Check if circuit breaker is open for the operation."""
        if operation_key not in self.circuit_breaker_state:
            return False
        
        state, last_failure, failure_count = self.circuit_breaker_state[operation_key]
        
        if state == "open":
            # Check if enough time has passed to try half-open
            if datetime.utcnow() - last_failure > timedelta(minutes=5):
                self.circuit_breaker_state[operation_key] = ("half_open", last_failure, failure_count)
                return False
            return True
        
        return False
    
    def _record_failure(self, operation_key: str, error: Exception) -> None:
        """Record a failure for circuit breaker logic."""
        now = datetime.utcnow()
        
        if operation_key not in self.circuit_breaker_state:
            self.circuit_breaker_state[operation_key] = ("closed", now, 1)
            return
        
        state, last_failure, failure_count = self.circuit_breaker_state[operation_key]
        
        # Increment failure count
        failure_count += 1
        
        # Open circuit if too many failures
        if failure_count >= 5:
            self.circuit_breaker_state[operation_key] = ("open", now, failure_count)
            self.logger.warning(
                "Circuit breaker opened",
                operation_key=operation_key,
                failure_count=failure_count
            )
        else:
            self.circuit_breaker_state[operation_key] = (state, now, failure_count)
    
    def _record_success(self, operation_key: str) -> None:
        """Record a success for circuit breaker logic."""
        if operation_key in self.circuit_breaker_state:
            state, last_failure, failure_count = self.circuit_breaker_state[operation_key]
            
            # Reset to closed state on success
            if state == "half_open":
                self.circuit_breaker_state[operation_key] = ("closed", last_failure, 0)
                self.logger.info(
                    "Circuit breaker reset to closed",
                    operation_key=operation_key
                )
    
    def get_circuit_breaker_status(self, operation_key: str) -> dict:
        """Get circuit breaker status for monitoring."""
        if operation_key not in self.circuit_breaker_state:
            return {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None
            }
        
        state, last_failure, failure_count = self.circuit_breaker_state[operation_key]
        return {
            "state": state,
            "failure_count": failure_count,
            "last_failure": last_failure.isoformat() if last_failure else None
        }
    
    def reset_circuit_breaker(self, operation_key: str) -> None:
        """Manually reset circuit breaker for an operation."""
        if operation_key in self.circuit_breaker_state:
            del self.circuit_breaker_state[operation_key]
            self.logger.info(
                "Circuit breaker manually reset",
                operation_key=operation_key
            )
