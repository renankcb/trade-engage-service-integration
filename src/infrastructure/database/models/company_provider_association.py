"""
Company Provider Association SQLAlchemy model.
"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class CompanyProviderAssociationModel(BaseModel):
    """Company Provider Association database model."""

    __tablename__ = "company_provider_associations"

    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    provider_type = Column(String(50), nullable=False, index=True)
    provider_config = Column(JSON, nullable=False)  # Credentials and settings
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    company = relationship("CompanyModel", back_populates="provider_associations")

    def __repr__(self) -> str:
        return f"<CompanyProviderAssociation(company_id={self.company_id}, provider_type={self.provider_type})>"
