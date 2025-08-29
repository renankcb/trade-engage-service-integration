"""add_claimed_at_field_to_job_routings

Revision ID: 1adfe0f8fab7
Revises: dd272f55cb0f
Create Date: 2025-08-27 16:06:36.021258

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1adfe0f8fab7"
down_revision: Union[str, Sequence[str], None] = "dd272f55cb0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add claimed_at field to job_routings table
    op.add_column(
        "job_routings",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create index for claimed_at field
    op.create_index("idx_job_routings_claimed_at", "job_routings", ["claimed_at"])

    # Note: sync_status is now a String field, so no need to add enum values

    # Add unique constraint to prevent duplicate routings
    op.create_unique_constraint(
        "uq_job_routings_job_company", "job_routings", ["job_id", "company_id_received"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint
    op.drop_constraint("uq_job_routings_job_company", "job_routings", type_="unique")

    # Remove PROCESSING status from enum (PostgreSQL doesn't support removing enum values easily)
    # This would require recreating the enum type

    # Remove index
    op.drop_index("idx_job_routings_claimed_at", table_name="job_routings")

    # Remove claimed_at column
    op.drop_column("job_routings", "claimed_at")
