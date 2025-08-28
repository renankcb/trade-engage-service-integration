"""merge_heads_provider_associations_and_job_categories

Revision ID: 2c6fc23421e6
Revises: 989b3b477569, fe67670b0e52
Create Date: 2025-08-27 21:56:47.060342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c6fc23421e6'
down_revision: Union[str, Sequence[str], None] = ('989b3b477569', 'fe67670b0e52')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
