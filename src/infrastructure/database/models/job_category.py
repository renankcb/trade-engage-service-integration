"""
Job Category SQLAlchemy model.
"""

from sqlalchemy import Column, Boolean, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import BaseModel


class JobCategoryModel(BaseModel):
    """Job Category database model."""

    __tablename__ = "job_categories"

    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_category_id = Column(
        UUID(as_uuid=True), ForeignKey("job_categories.id"), nullable=True, index=True
    )  # For hierarchical categories
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    parent_category = relationship("JobCategoryModel", remote_side="JobCategoryModel.id")
    sub_categories = relationship("JobCategoryModel", back_populates="parent_category")

    def __repr__(self) -> str:
        return f"<JobCategory(name={self.name}, parent={self.parent_category_id})>"
