"""
Health check endpoints for the application.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db_session
from src.config.logging import get_logger
from src.infrastructure.monitoring.health_checks import HealthChecker
from src.infrastructure.monitoring.metrics import get_metrics, get_metrics_content_type

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


async def get_health_checker(
    db: AsyncSession = Depends(get_db_session),
) -> HealthChecker:
    """Get health checker instance."""
    return HealthChecker(db)


@router.get("/")
async def health_check(
    health_checker: HealthChecker = Depends(get_health_checker),
) -> Dict[str, Any]:
    """Basic health check endpoint."""
    try:
        is_healthy = await health_checker.check_readiness()

        if is_healthy:
            return {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",  # TODO: Add actual timestamp
            }
        else:
            return {
                "status": "unhealthy",
                "timestamp": "2024-01-01T00:00:00Z",  # TODO: Add actual timestamp
            }

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/ready")
async def readiness_check(
    health_checker: HealthChecker = Depends(get_health_checker),
) -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    try:
        is_ready = await health_checker.check_readiness()

        if is_ready:
            return {
                "status": "ready",
                "timestamp": "2024-01-01T00:00:00Z",  # TODO: Add actual timestamp
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {str(e)}",
        )


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": "2024-01-01T00:00:00Z",  # TODO: Add actual timestamp
    }


@router.get("/detailed")
async def detailed_health_check(
    health_checker: HealthChecker = Depends(get_health_checker),
) -> Dict[str, Any]:
    """Detailed health check with all components."""
    try:
        health_status = await health_checker.check_all_components()

        return {
            "status": "success",
            "data": health_status,
            "timestamp": "2024-01-01T00:00:00Z",  # TODO: Add actual timestamp
        }

    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detailed health check failed: {str(e)}",
        )


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint."""
    try:
        metrics_data = get_metrics()
        content_type = get_metrics_content_type()

        logger.debug("Prometheus metrics requested")

        return Response(content=metrics_data, media_type=content_type)

    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics",
        )
