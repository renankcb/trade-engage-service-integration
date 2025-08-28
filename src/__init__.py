"""
ServiceTitan Integration Service.

A service for integrating job management with external service providers.
"""

__version__ = "0.1.0"
__author__ = "TradeEngage Team"
__description__ = "ServiceTitan Integration Service"

from .api import create_app
from .background import celery_app, setup_periodic_tasks
from .config import settings

__all__ = [
    "create_app",
    "celery_app",
    "setup_periodic_tasks",
    "settings",
]
