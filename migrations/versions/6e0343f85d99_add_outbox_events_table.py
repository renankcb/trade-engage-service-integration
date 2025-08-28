"""add_outbox_events_table

Revision ID: 6e0343f85d99
Revises: 698b53ad52db
Create Date: 2025-08-27 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e0343f85d99'
down_revision: Union[str, Sequence[str], None] = '698b53ad52db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Create outbox_events table for transactional outbox pattern
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('aggregate_id', sa.String(255), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_outbox_events_status', 'outbox_events', ['status'])
    op.create_index('idx_outbox_events_type', 'outbox_events', ['event_type'])
    op.create_index('idx_outbox_events_created', 'outbox_events', ['created_at'])
    op.create_index('idx_outbox_events_aggregate', 'outbox_events', ['aggregate_id'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove indexes
    op.drop_index('idx_outbox_events_aggregate', table_name='outbox_events')
    op.drop_index('idx_outbox_events_created', table_name='outbox_events')
    op.drop_index('idx_outbox_events_type', table_name='outbox_events')
    op.drop_index('idx_outbox_events_status', table_name='outbox_events')
    
    # Remove table
    op.drop_table('outbox_events')
