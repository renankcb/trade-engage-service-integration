"""
Admin routes for system management and monitoring.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db_session
from src.background.workers import WorkerManager
from src.config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


async def get_worker_manager(
    db: AsyncSession = Depends(get_db_session)
) -> WorkerManager:
    """Get worker manager instance."""
    return WorkerManager(db)


@router.get("/workers/status")
async def get_workers_status(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Get status of all background workers."""
    try:
        status_info = worker_manager.get_health_status()
        
        logger.info("Workers status requested")
        
        return {
            "status": "success",
            "data": status_info,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add actual timestamp
        }
        
    except Exception as e:
        logger.error("Error getting workers status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workers status: {str(e)}"
        )


@router.get("/workers/stats")
async def get_workers_stats(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Get detailed statistics from all workers."""
    try:
        stats = worker_manager.get_worker_stats()
        
        logger.info("Workers stats requested")
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add actual timestamp
        }
        
    except Exception as e:
        logger.error("Error getting workers stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workers stats: {str(e)}"
        )


@router.post("/workers/start")
async def start_workers(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Start all background workers."""
    try:
        await worker_manager.start_all_workers()
        
        logger.info("All workers started via admin API")
        
        return {
            "status": "success",
            "message": "All background workers started successfully",
            "data": {
                "workers_running": True,
                "active_workers": len(worker_manager.worker_tasks)
            }
        }
        
    except Exception as e:
        logger.error("Error starting workers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workers: {str(e)}"
        )


@router.post("/workers/stop")
async def stop_workers(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Stop all background workers."""
    try:
        await worker_manager.stop_all_workers()
        
        logger.info("All workers stopped via admin API")
        
        return {
            "status": "success",
            "message": "All background workers stopped successfully",
            "data": {
                "workers_running": False,
                "active_workers": 0
            }
        }
        
    except Exception as e:
        logger.error("Error stopping workers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop workers: {str(e)}"
        )


@router.post("/workers/{worker_name}/restart")
async def restart_worker(
    worker_name: str,
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Restart a specific worker."""
    try:
        await worker_manager.restart_worker(worker_name)
        
        logger.info(f"Worker {worker_name} restarted via admin API")
        
        return {
            "status": "success",
            "message": f"Worker {worker_name} restarted successfully",
            "data": {
                "worker_name": worker_name,
                "status": "restarted"
            }
        }
        
    except ValueError as e:
        logger.warning(f"Invalid worker name: {worker_name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid worker name: {worker_name}"
        )
        
    except Exception as e:
        logger.error(f"Error restarting worker {worker_name}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart worker {worker_name}: {str(e)}"
        )


@router.get("/system/health")
async def get_system_health(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Get overall system health status."""
    try:
        workers_status = worker_manager.get_health_status()
        
        # Determine overall system health
        overall_status = "healthy"
        if not workers_status["status"] == "healthy":
            overall_status = "degraded"
        
        # Check if critical workers are running
        critical_workers = ["outbox", "sync"]
        critical_workers_status = all(
            workers_status["workers"][worker]["status"] == "running"
            for worker in critical_workers
        )
        
        if not critical_workers_status:
            overall_status = "critical"
        
        health_info = {
            "system_status": overall_status,
            "workers": workers_status,
            "critical_services": {
                "database": "healthy",  # TODO: Add actual DB health check
                "redis": "healthy",     # TODO: Add actual Redis health check
                "providers": "healthy"  # TODO: Add actual provider health check
            },
            "recommendations": []
        }
        
        # Add recommendations based on status
        if overall_status == "degraded":
            health_info["recommendations"].append(
                "Some workers are not running optimally. Consider restarting them."
            )
        
        if overall_status == "critical":
            health_info["recommendations"].append(
                "Critical workers are not running. Immediate attention required."
            )
        
        logger.info("System health check requested", status=overall_status)
        
        return {
            "status": "success",
            "data": health_info,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add actual timestamp
        }
        
    except Exception as e:
        logger.error("Error getting system health", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/system/metrics")
async def get_system_metrics(
    worker_manager: WorkerManager = Depends(get_worker_manager)
) -> Dict[str, Any]:
    """Get system metrics for monitoring."""
    try:
        workers_stats = worker_manager.get_worker_stats()
        
        # Calculate key metrics
        total_tasks = sum(
            workers_stats[worker].get("total_syncs", 0) + 
            workers_stats[worker].get("total_polls", 0) + 
            workers_stats[worker].get("total_processed", 0)
            for worker in ["sync_worker", "poll_worker", "outbox_worker"]
        )
        
        total_errors = sum(
            workers_stats[worker].get("total_errors", 0) + 
            workers_stats[worker].get("error_count", 0)
            for worker in ["sync_worker", "poll_worker", "outbox_worker"]
        )
        
        overall_success_rate = (
            (total_tasks - total_errors) / total_tasks * 100
            if total_tasks > 0 else 100.0
        )
        
        metrics = {
            "performance": {
                "total_tasks_processed": total_tasks,
                "total_errors": total_errors,
                "overall_success_rate": round(overall_success_rate, 2),
                "active_workers": workers_stats["manager"]["active_workers"]
            },
            "workers": workers_stats,
            "queues": {
                "sync": "active",      # TODO: Add actual queue status
                "poll": "active",      # TODO: Add actual queue status
                "retry": "active",     # TODO: Add actual queue status
                "maintenance": "active" # TODO: Add actual queue status
            }
        }
        
        logger.info("System metrics requested")
        
        return {
            "status": "success",
            "data": metrics,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add actual timestamp
        }
        
    except Exception as e:
        logger.error("Error getting system metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )
