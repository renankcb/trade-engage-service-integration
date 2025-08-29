"""Fix job_routings schema add missing fields

Revision ID: dd272f55cb0f
Revises: 9c4ab929ae1c
Create Date: 2025-08-27 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd272f55cb0f"
down_revision: Union[str, Sequence[str], None] = "9c4ab929ae1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add missing fields to job_routings table."""

    # Add missing columns to job_routings table
    op.add_column(
        "job_routings",
        sa.Column(
            "sync_status", sa.String(50), nullable=False, server_default="pending"
        ),
    )
    op.add_column(
        "job_routings", sa.Column("external_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "job_routings", sa.Column("last_synced_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "job_routings",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("job_routings", sa.Column("error_message", sa.Text(), nullable=True))

    # Add indexes for performance
    op.create_index("ix_job_routings_sync_status", "job_routings", ["sync_status"])
    op.create_index("ix_job_routings_external_id", "job_routings", ["external_id"])
    op.create_index(
        "ix_job_routings_last_synced_at", "job_routings", ["last_synced_at"]
    )


def downgrade() -> None:
    """Downgrade schema - remove added fields from job_routings table."""

    # Drop indexes
    op.drop_index("ix_job_routings_last_synced_at", "job_routings")
    op.drop_index("ix_job_routings_external_id", "job_routings")
    op.drop_index("ix_job_routings_sync_status", "job_routings")

    # Drop columns
    op.drop_column("job_routings", "error_message")
    op.drop_column("job_routings", "retry_count")
    op.drop_column("job_routings", "last_synced_at")
    op.drop_column("job_routings", "external_id")
    op.drop_column("job_routings", "sync_status")
