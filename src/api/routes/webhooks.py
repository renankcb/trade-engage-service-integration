"""
Webhook endpoints for provider callbacks.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.common import BaseResponse
from src.api.schemas.provider import WebhookPayload
from src.config.database import get_db_session
from src.config.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/webhooks/servicetitan", response_model=BaseResponse)
async def servicetitan_webhook(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
):
    """Handle ServiceTitan webhook callbacks."""
    # TODO: Implement ServiceTitan webhook processing
    logger.info("ServiceTitan webhook received", event_type=payload.event_type)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ServiceTitan webhooks not yet implemented",
    )


@router.post("/webhooks/housecallpro", response_model=BaseResponse)
async def housecallpro_webhook(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
):
    """Handle HousecallPro webhook callbacks."""
    # TODO: Implement HousecallPro webhook processing
    logger.info("HousecallPro webhook received", event_type=payload.event_type)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="HousecallPro webhooks not yet implemented",
    )


@router.post("/webhooks/generic", response_model=BaseResponse)
async def generic_webhook(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db_session),
):
    """Handle generic provider webhook callbacks."""
    # TODO: Implement generic webhook processing
    logger.info("Generic webhook received", provider=payload.provider)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Generic webhooks not yet implemented",
    )
