"""
External rate limiting utilities.
"""

from typing import Dict, Any, Optional
import time
import structlog

logger = structlog.get_logger()


class ExternalRateLimiter:
    """Rate limiter for external API calls."""
    
    def __init__(self):
        self.request_counts: Dict[str, list] = {}
        self.rate_limits: Dict[str, Dict[str, int]] = {}
    
    def configure_provider(
        self, 
        provider_name: str, 
        requests_per_minute: int,
        requests_per_hour: int = 0
    ):
        """Configure rate limits for a provider."""
        self.rate_limits[provider_name] = {
            "per_minute": requests_per_minute,
            "per_hour": requests_per_hour or (requests_per_minute * 60)
        }
        
        logger.info(
            "Rate limits configured for provider",
            provider=provider_name,
            per_minute=requests_per_minute,
            per_hour=requests_per_hour or (requests_per_minute * 60)
        )
    
    def is_allowed(self, provider_name: str, endpoint: str = "general") -> bool:
        """Check if request is allowed."""
        if provider_name not in self.rate_limits:
            return True  # No limits configured
        
        key = f"{provider_name}:{endpoint}"
        limits = self.rate_limits[provider_name]
        current_time = time.time()
        
        # Clean old requests
        if key in self.request_counts:
            self.request_counts[key] = [
                req_time for req_time in self.request_counts[key]
                if current_time - req_time < 3600  # Keep last hour
            ]
        else:
            self.request_counts[key] = []
        
        # Check minute limit
        minute_ago = current_time - 60
        requests_last_minute = sum(
            1 for req_time in self.request_counts[key]
            if req_time > minute_ago
        )
        
        if requests_last_minute >= limits["per_minute"]:
            logger.warning(
                "Rate limit exceeded for provider",
                provider=provider_name,
                endpoint=endpoint,
                requests_last_minute=requests_last_minute,
                limit=limits["per_minute"]
            )
            return False
        
        # Check hour limit
        hour_ago = current_time - 3600
        requests_last_hour = sum(
            1 for req_time in self.request_counts[key]
            if req_time > hour_ago
        )
        
        if requests_last_hour >= limits["per_hour"]:
            logger.warning(
                "Hourly rate limit exceeded for provider",
                provider=provider_name,
                endpoint=endpoint,
                requests_last_hour=requests_last_hour,
                limit=limits["per_hour"]
            )
            return False
        
        return True
    
    def record_request(self, provider_name: str, endpoint: str = "general"):
        """Record a request for rate limiting."""
        key = f"{provider_name}:{endpoint}"
        current_time = time.time()
        
        if key not in self.request_counts:
            self.request_counts[key] = []
        
        self.request_counts[key].append(current_time)
        
        logger.debug(
            "Request recorded for rate limiting",
            provider=provider_name,
            endpoint=endpoint,
            total_requests=len(self.request_counts[key])
        )
    
    def get_remaining_quota(
        self, 
        provider_name: str, 
        endpoint: str = "general"
    ) -> Dict[str, int]:
        """Get remaining quota for a provider."""
        if provider_name not in self.rate_limits:
            return {
                "per_minute": 0,
                "per_hour": 0,
                "unlimited": True
            }
        
        key = f"{provider_name}:{endpoint}"
        limits = self.rate_limits[provider_name]
        current_time = time.time()
        
        if key not in self.request_counts:
            return {
                "per_minute": limits["per_minute"],
                "per_hour": limits["per_hour"],
                "unlimited": False
            }
        
        # Calculate remaining quota
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        requests_last_minute = sum(
            1 for req_time in self.request_counts[key]
            if req_time > minute_ago
        )
        
        requests_last_hour = sum(
            1 for req_time in self.request_counts[key]
            if req_time > hour_ago
        )
        
        return {
            "per_minute": max(0, limits["per_minute"] - requests_last_minute),
            "per_hour": max(0, limits["per_hour"] - requests_last_hour),
            "unlimited": False
        }
    
    def wait_for_quota(
        self, 
        provider_name: str, 
        endpoint: str = "general",
        max_wait: int = 60
    ) -> bool:
        """Wait for quota to become available."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.is_allowed(provider_name, endpoint):
                return True
            
            # Wait before next check
            time.sleep(1)
        
        logger.warning(
            "Timeout waiting for quota",
            provider=provider_name,
            endpoint=endpoint,
            max_wait=max_wait
        )
        return False
    
    def clear_provider_data(self, provider_name: str):
        """Clear rate limiting data for a provider."""
        keys_to_remove = [
            key for key in self.request_counts.keys()
            if key.startswith(f"{provider_name}:")
        ]
        
        for key in keys_to_remove:
            del self.request_counts[key]
        
        if provider_name in self.rate_limits:
            del self.rate_limits[provider_name]
        
        logger.info(
            "Rate limiting data cleared for provider",
            provider=provider_name
        )


# Global rate limiter instance
external_rate_limiter = ExternalRateLimiter()


def get_external_rate_limiter() -> ExternalRateLimiter:
    """Get the global external rate limiter instance."""
    return external_rate_limiter
