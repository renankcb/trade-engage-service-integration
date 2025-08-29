"""Move revenue column from jobs to job_routings table.

This migration:
1. Adds revenue column to job_routings table
2. Migrates existing revenue data from jobs to job_routings
3. Removes revenue column from jobs table

Revision ID: move_revenue_to_job_routing
Revises: 9c4ab929ae1c
Create Date: 2025-08-29 16:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "move_revenue_to_job_routing"
down_revision = "9c4ab929ae1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema - move revenue from jobs to job_routings."""

    # 1. Add revenue column to job_routings table
    op.add_column(
        "job_routings",
        sa.Column("revenue", sa.Numeric(precision=10, scale=2), nullable=True),
    )

    # 2. Create index on revenue column for performance
    op.create_index("ix_job_routings_revenue", "job_routings", ["revenue"])

    # 3. Migrate existing revenue data from jobs to job_routings
    # This will set revenue for all existing job_routings based on their job's revenue
    op.execute(
        """
        UPDATE job_routings
        SET revenue = jobs.revenue
        FROM jobs
        WHERE job_routings.job_id = jobs.id
        AND jobs.revenue IS NOT NULL
    """
    )

    # 4. Remove revenue column from jobs table
    # Note: No index to drop as it was never created
    op.drop_column("jobs", "revenue")


def downgrade() -> None:
    """Downgrade schema - restore revenue column to jobs table."""

    # 1. Add revenue column back to jobs table
    op.add_column(
        "jobs", sa.Column("revenue", sa.Numeric(precision=10, scale=2), nullable=True)
    )

    # 2. Create index on revenue column
    op.create_index("ix_jobs_revenue", "jobs", ["revenue"])

    # 3. Migrate revenue data back from job_routings to jobs
    # This will restore revenue to jobs based on the first job_routing with revenue
    op.execute(
        """
        UPDATE jobs
        SET revenue = job_routings.revenue
        FROM job_routings
        WHERE jobs.id = job_routings.job_id
        AND job_routings.revenue IS NOT NULL
    """
    )

    # 4. Remove revenue column from job_routings table
    op.drop_index("ix_job_routings_revenue", table_name="job_routings")
    op.drop_column("job_routings", "revenue")
