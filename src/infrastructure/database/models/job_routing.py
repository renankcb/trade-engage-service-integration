"""
Job Routing SQLAlchemy model.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from src.domain.value_objects.sync_status import SyncStatus

from . import BaseModel


class JobRoutingModel(BaseModel):
    """Job Routing database model."""

    __tablename__ = "job_routings"

    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    company_id_received = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    external_id = Column(String(255), unique=True, index=True)
    sync_status = Column(
        String(50),
        default=SyncStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    retry_count = Column(Integer, default=0, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), index=True)
    error_message = Column(Text)

    # Additional fields for tracking
    next_retry_at = Column(DateTime(timezone=True), index=True)
    total_sync_attempts = Column(Integer, default=0, nullable=False)
    claimed_at = Column(DateTime(timezone=True), index=True)

    # Revenue field
    revenue = Column(Numeric(precision=10, scale=2), nullable=True, index=True)

    # Relationships
    job = relationship("JobModel", back_populates="job_routings")
    company_received = relationship(
        "CompanyModel", back_populates="received_job_routings"
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index(
            "idx_job_routing_sync_status_company", "sync_status", "company_id_received"
        ),
        Index("idx_job_routing_last_synced", "last_synced_at", "sync_status"),
        Index("idx_job_routing_retry", "sync_status", "retry_count", "next_retry_at"),
        Index("idx_job_routing_claimed", "claimed_at", "sync_status"),
        Index("idx_job_routing_revenue", "revenue"),  # New index for revenue
        # UNIQUE constraint to prevent duplicate routings for the same job+company
        Index("idx_job_routing_unique", "job_id", "company_id_received", unique=True),
    )

    def __repr__(self) -> str:
        return f"<JobRouting(id={self.id}, job_id={self.job_id}, status={self.sync_status})>"
