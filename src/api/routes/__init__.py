"""
API routes package.
"""

from .admin import router as admin_router
from .health import router as health_router
from .jobs import router as jobs_router
from .webhooks import router as webhooks_router

__all__ = [
    "admin_router",
    "health_router",
    "jobs_router",
    "webhooks_router",
]
