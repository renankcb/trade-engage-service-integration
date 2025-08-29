"""
Job-related API schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects.sync_status import SyncStatus

from .common import TimestampMixin


class AddressSchema(BaseModel):
    """Address schema."""

    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        return v.upper()


class HomeownerSchema(BaseModel):
    """Homeowner contact schema."""

    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)


class JobCreateRequest(BaseModel):
    """Job creation request schema."""

    summary: str = Field(..., min_length=1, max_length=1000)
    address: AddressSchema
    homeowner: HomeownerSchema
    created_by_company_id: UUID = Field(
        ..., description="Company that REQUESTED the job"
    )
    created_by_technician_id: UUID = Field(
        ..., description="Technician that IDENTIFIED the need"
    )

    # Job skills and classification
    required_skills: Optional[list[str]] = Field(
        None,
        description="List of skills required for this job (e.g., ['plumbing', 'electrical'])",
    )
    skill_levels: Optional[dict[str, str]] = Field(
        None,
        description="Skill name to required level mapping (e.g., {'plumbing': 'expert', 'electrical': 'intermediate'})",
    )


class JobResponse(TimestampMixin):
    """Job response schema."""

    id: UUID
    summary: str
    address: AddressSchema
    homeowner: HomeownerSchema
    created_by_company_id: UUID = Field(
        ..., description="Company that REQUESTED the job"
    )
    created_by_technician_id: UUID = Field(
        ..., description="Technician that IDENTIFIED the need"
    )
    status: str = Field(..., description="Current job status")
    completed_at: Optional[datetime] = Field(
        None, description="Job completion timestamp"
    )
    selected_company_id: Optional[UUID] = Field(
        None, description="Company selected to execute the job"
    )
    matching_score: Optional[float] = Field(
        None, description="Matching score for the selected company"
    )

    model_config = {"from_attributes": True}


class JobRoutingResponse(TimestampMixin):
    """Job routing response schema."""

    id: UUID
    job_id: UUID
    company_id_received: UUID
    external_id: Optional[str]
    sync_status: SyncStatus
    retry_count: int
    last_synced_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class JobRoutingCreateRequest(BaseModel):
    """Job routing creation request."""

    job_id: UUID
    company_id_received: UUID


class SyncStatusUpdateRequest(BaseModel):
    """Sync status update request."""

    sync_status: SyncStatus
    external_id: Optional[str] = None
    error_message: Optional[str] = None
