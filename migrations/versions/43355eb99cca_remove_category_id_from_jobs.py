"""remove_category_id_from_jobs

Revision ID: 43355eb99cca
Revises: 2c6fc23421e6
Create Date: 2025-08-28 13:11:26.648700

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "43355eb99cca"
down_revision: Union[str, Sequence[str], None] = "2c6fc23421e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove index first
    op.drop_index("idx_jobs_category_id", table_name="jobs")

    # Remove foreign key constraint
    op.drop_constraint("fk_jobs_category_id_job_categories", "jobs", type_="foreignkey")

    # Remove category_id column
    op.drop_column("jobs", "category_id")


def downgrade() -> None:
    """Downgrade schema."""
    # Add category_id column back
    op.add_column("jobs", sa.Column("category_id", sa.UUID(), nullable=True))

    # Add foreign key constraint back
    op.create_foreign_key(
        "fk_jobs_category_id_job_categories",
        "jobs",
        "job_categories",
        ["category_id"],
        ["id"],
    )

    # Add index back
    op.create_index("idx_jobs_category_id", "jobs", ["category_id"])
