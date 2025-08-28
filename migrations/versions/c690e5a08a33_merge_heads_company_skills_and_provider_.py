"""merge_heads_company_skills_and_provider_associations

Revision ID: c690e5a08a33
Revises: 39a4593f6696, 8919a5025a32
Create Date: 2025-08-27 21:52:07.360507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c690e5a08a33'
down_revision: Union[str, Sequence[str], None] = ('39a4593f6696', '8919a5025a32')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
