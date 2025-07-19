"""Rename user_crops table to growings

Revision ID: rename_user_crops_to_growings
Revises: 7ce61253f2a8
Create Date: 2025-07-19 15:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_user_crops_to_growings'
down_revision = '7ce61253f2a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Copy data from user_crops to growings with explicit column mapping
    op.execute("""
        INSERT INTO growings (id, user_id, crop_id, notes, created_at, updated_at)
        SELECT id, user_id, crop_id, notes, created_at, updated_at FROM user_crops
    """)
    op.drop_table('user_crops')


def downgrade() -> None:
    # Recreate user_crops table and copy data back
    op.create_table('user_crops',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('crop_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crop_id'], ['crops.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.execute("INSERT INTO user_crops SELECT * FROM growings")