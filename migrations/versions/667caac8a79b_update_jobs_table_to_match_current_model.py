"""update_jobs_table_to_match_current_model

Revision ID: 667caac8a79b
Revises: 43355eb99cca
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "667caac8a79b"
down_revision: Union[str, Sequence[str], None] = "2c6fc23421e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - update jobs table to match current model."""

    # Add new columns to jobs table (only those that don't exist)
    op.add_column(
        "jobs", sa.Column("created_by_technician_id", sa.UUID(), nullable=True)
    )

    # Address fields
    op.add_column("jobs", sa.Column("street", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("jobs", sa.Column("state", sa.String(2), nullable=True))
    op.add_column("jobs", sa.Column("zip_code", sa.String(10), nullable=True))

    # Homeowner contact info
    op.add_column("jobs", sa.Column("homeowner_name", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("homeowner_phone", sa.String(20), nullable=True))
    op.add_column("jobs", sa.Column("homeowner_email", sa.String(255), nullable=True))

    # Note: category, required_skills, and skill_levels already exist

    # Update existing columns to match new schema
    # Change title to summary (if title exists)
    try:
        op.alter_column("jobs", "title", new_column_name="summary")
    except Exception:
        pass  # Column might not exist or already renamed

    # Add foreign key constraint for technician
    op.create_foreign_key(
        "fk_jobs_technician_id_technicians",
        "jobs",
        "technicians",
        ["created_by_technician_id"],
        ["id"],
    )

    # Create indexes for performance
    op.create_index(
        "ix_jobs_created_by_technician_id", "jobs", ["created_by_technician_id"]
    )
    op.create_index("ix_jobs_street", "jobs", ["street"])
    op.create_index("ix_jobs_city", "jobs", ["city"])
    op.create_index("ix_jobs_state", "jobs", ["state"])
    op.create_index("ix_jobs_zip_code", "jobs", ["zip_code"])
    op.create_index("ix_jobs_homeowner_name", "jobs", ["homeowner_name"])

    # Create composite indexes for common queries
    op.create_index("ix_jobs_location_composite", "jobs", ["city", "state"])
    op.create_index(
        "ix_jobs_company_technician",
        "jobs",
        ["created_by_company_id", "created_by_technician_id"],
    )

    # Make summary not nullable after data migration
    # First, ensure all summary fields have data
    op.execute(
        "UPDATE jobs SET summary = COALESCE(summary, 'Job description') WHERE summary IS NULL"
    )
    op.alter_column("jobs", "summary", nullable=False)

    # Make address fields not nullable after ensuring data
    op.execute(
        "UPDATE jobs SET street = COALESCE(street, 'Address not specified') WHERE street IS NULL"
    )
    op.execute(
        "UPDATE jobs SET city = COALESCE(city, 'City not specified') WHERE city IS NULL"
    )
    op.execute("UPDATE jobs SET state = COALESCE(state, 'ST') WHERE state IS NULL")
    op.execute(
        "UPDATE jobs SET zip_code = COALESCE(zip_code, '00000') WHERE zip_code IS NULL"
    )
    op.execute(
        "UPDATE jobs SET homeowner_name = COALESCE(homeowner_name, 'Homeowner not specified') WHERE homeowner_name IS NULL"
    )

    op.alter_column("jobs", "street", nullable=False)
    op.alter_column("jobs", "city", nullable=False)
    op.alter_column("jobs", "state", nullable=False)
    op.alter_column("jobs", "zip_code", nullable=False)
    op.alter_column("jobs", "homeowner_name", nullable=False)


def downgrade() -> None:
    """Downgrade schema - revert jobs table changes."""

    # Drop indexes
    op.drop_index("ix_jobs_company_technician", table_name="jobs")
    op.drop_index("ix_jobs_location_composite", table_name="jobs")
    op.drop_index("ix_jobs_homeowner_name", table_name="jobs")
    op.drop_index("ix_jobs_zip_code", table_name="jobs")
    op.drop_index("ix_jobs_state", table_name="jobs")
    op.drop_index("ix_jobs_city", table_name="jobs")
    op.drop_index("ix_jobs_street", table_name="jobs")
    op.drop_index("ix_jobs_created_by_technician_id", table_name="jobs")

    # Drop foreign key constraint
    op.drop_constraint("fk_jobs_technician_id_technicians", "jobs", type_="foreignkey")

    # Drop columns
    op.drop_column("jobs", "skill_levels")
    op.drop_column("jobs", "required_skills")
    op.drop_column("jobs", "homeowner_email")
    op.drop_column("jobs", "homeowner_phone")
    op.drop_column("jobs", "homeowner_name")
    op.drop_column("jobs", "zip_code")
    op.drop_column("jobs", "state")
    op.drop_column("jobs", "city")
    op.drop_column("jobs", "street")
    op.drop_column("jobs", "summary")
    op.drop_column("jobs", "created_by_technician_id")
