"""Add notes column to user_crops table

Revision ID: 7ce61253f2a8
Revises: add_user_crops_table
Create Date: 2025-07-19 06:19:43.821509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7ce61253f2a8'
down_revision: Union[str, None] = 'add_user_crops_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add notes column to user_crops table
    op.add_column('user_crops', sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))


def downgrade() -> None:
    # Remove notes column from user_crops table
    op.drop_column('user_crops', 'notes')
