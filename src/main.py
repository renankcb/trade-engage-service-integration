"""
Main application entry point.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.app import create_app
from src.background.workers import WorkerManager
from src.config.database import get_db_session
from src.config.logging import get_logger

logger = get_logger(__name__)

# Global worker manager
worker_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global worker_manager

    # Startup
    logger.info("Starting TradeEngage Service Integration")

    try:
        # Initialize database connection
        db_session = await get_db_session().__anext__()

        # Initialize and start workers
        worker_manager = WorkerManager(db_session)
        await worker_manager.start_all_workers()

        logger.info("All workers started successfully")

        yield

    except Exception as e:
        logger.error("Error during startup", error=str(e))
        raise

    finally:
        # Shutdown
        logger.info("Shutting down TradeEngage Service Integration")

        if worker_manager:
            try:
                await worker_manager.stop_all_workers()
                logger.info("All workers stopped successfully")
            except Exception as e:
                logger.error("Error stopping workers", error=str(e))


def create_main_app() -> FastAPI:
    """Create the main FastAPI application."""
    app = create_app()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add lifespan manager
    app.router.lifespan_context = lifespan

    return app


# Create the main app
app = create_main_app()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down gracefully")

    if worker_manager:
        try:
            # Stop workers in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(worker_manager.stop_all_workers())
            loop.close()
        except Exception as e:
            logger.error("Error stopping workers during shutdown", error=str(e))

    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting TradeEngage Service Integration server")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        log_level="info",
    )
