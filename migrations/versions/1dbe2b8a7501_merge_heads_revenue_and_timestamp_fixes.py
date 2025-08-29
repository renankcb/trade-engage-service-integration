"""merge_heads_revenue_and_timestamp_fixes

Revision ID: 1dbe2b8a7501
Revises: 5d055f4425ca, move_revenue_to_job_routing
Create Date: 2025-08-29 15:06:48.402257

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1dbe2b8a7501"
down_revision: Union[str, Sequence[str], None] = (
    "5d055f4425ca",
    "move_revenue_to_job_routing",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
