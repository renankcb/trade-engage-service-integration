"""
Health check implementations for the application.
"""

from typing import Dict, Any, Optional
import asyncio
import structlog
from src.infrastructure.database.connection import get_database_health
from src.infrastructure.external.http_client import get_redis_health

logger = structlog.get_logger()


class HealthChecker:
    """Health checker for application components."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            # "external_apis": self._check_external_apis,
        }
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        
        for check_name, check_func in self.checks.items():
            try:
                results[check_name] = await check_func()
            except Exception as e:
                logger.error(
                    "Health check failed",
                    check_name=check_name,
                    error=str(e)
                )
                results[check_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            health_info = await get_database_health()
            
            if health_info["status"] == "healthy":
                return {
                    "status": "healthy",
                    "response_time_ms": health_info.get("response_time_ms", 0),
                    "connections": health_info.get("connections", 0)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": health_info.get("error", "Unknown database error")
                }
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            health_info = await get_redis_health()
            
            if health_info["status"] == "healthy":
                return {
                    "status": "healthy",
                    "response_time_ms": health_info.get("response_time_ms", 0),
                    "memory_usage": health_info.get("memory_usage", 0)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": health_info.get("error", "Unknown Redis error")
                }
                
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _check_external_apis(self) -> Dict[str, Any]:
        """Check external API health."""
        try:
            # Check ServiceTitan API
            servicetitan_health = await self._check_servicetitan_api()
            
            # Check other external APIs here
            external_apis = {
                "servicetitan": servicetitan_health,
                # Add other APIs as needed
            }
            
            # Overall status
            all_healthy = all(
                api["status"] == "healthy" 
                for api in external_apis.values()
            )
            
            return {
                "status": "healthy" if all_healthy else "unhealthy",
                "apis": external_apis,
                "healthy_count": sum(
                    1 for api in external_apis.values() 
                    if api["status"] == "healthy"
                ),
                "total_count": len(external_apis)
            }
            
        except Exception as e:
            logger.error("External APIs health check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _check_servicetitan_api(self) -> Dict[str, Any]:
        """Check ServiceTitan API health."""
        try:
            # Import here to avoid circular imports
            from src.infrastructure.providers.servicetitan.client import (
                ServiceTitanClient
            )
            
            # Create a test client with mock credentials
            client = ServiceTitanClient(
                client_id="test",
                client_secret="test", 
                tenant_id="test"
            )
            
            # Test connection
            response_time = await client.test_connection()
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "last_check": "2024-01-01T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(
                "ServiceTitan API health check failed",
                error=str(e)
            )
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": "2024-01-01T00:00:00Z"
            }
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall application health status."""
        try:
            health_results = await self.run_health_checks()
            
            # Determine overall status
            critical_services = ["database", "redis"]
            critical_healthy = all(
                health_results.get(service, {}).get("status") == "healthy"
                for service in critical_services
            )
            
            if critical_healthy:
                overall_status = "healthy"
            else:
                overall_status = "unhealthy"
            
            return {
                "status": overall_status,
                "timestamp": "2024-01-01T00:00:00Z",
                "services": health_results,
                "critical_services_healthy": critical_healthy
            }
            
        except Exception as e:
            logger.error("Overall health check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }

    async def check_readiness(self):
        """Check if the service is ready to receive traffic."""
        try:
            health_results = await self.run_health_checks()
            
            # Critical services that must be healthy
            critical_services = ["database", "redis"]
            critical_healthy = all(
                health_results.get(service, {}).get("status") == "healthy"
                for service in critical_services
            )
            
            return type('HealthStatus', (), {
                'is_healthy': critical_healthy,
                'checks': health_results,
                'timestamp': "2024-01-01T00:00:00Z"
            })()
            
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return type('HealthStatus', (), {
                'is_healthy': False,
                'checks': {},
                'timestamp': "2024-01-01T00:00:00Z"
            })()

    async def check_all_components(self):
        """Check all system components."""
        try:
            health_results = await self.run_health_checks()
            
            # Determine overall status
            all_healthy = all(
                health_results.get(service, {}).get("status") == "healthy"
                for service in health_results.keys()
            )
            
            return type('DetailedHealthStatus', (), {
                'is_healthy': all_healthy,
                'components': health_results,
                'overall_health': "healthy" if all_healthy else "unhealthy",
                'timestamp': "2024-01-01T00:00:00Z"
            })()
            
        except Exception as e:
            logger.error("Detailed health check failed", error=str(e))
            return type('DetailedHealthStatus', (), {
                'is_healthy': False,
                'components': {},
                'overall_health': "error",
                'timestamp': "2024-01-01T00:00:00Z"
            })()


# Global health checker instance
health_checker = HealthChecker(db_session=None)


async def get_application_health() -> Dict[str, Any]:
    """Get application health status."""
    return await health_checker.get_overall_health()


async def get_service_health(service_name: str) -> Optional[Dict[str, Any]]:
    """Get health status for a specific service."""
    if service_name not in health_checker.checks:
        return None
    
    try:
        check_func = health_checker.checks[service_name]
        return await check_func()
    except Exception as e:
        logger.error(
            "Service health check failed",
            service=service_name,
            error=str(e)
        )
        return {
            "status": "error",
            "error": str(e)
        }
