"""Add city column to weather_areas table

Revision ID: add_city_to_weather_areas
Revises: rename_user_crops_to_growings
Create Date: 2025-07-19 17:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_city_to_weather_areas'
down_revision = 'rename_user_crops_to_growings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add city column to weather_areas table
    op.add_column('weather_areas', sa.Column('city', sa.String(), nullable=False, server_default=''))
    op.create_index('ix_weather_areas_city', 'weather_areas', ['city'])


def downgrade() -> None:
    # Remove city column from weather_areas table
    op.drop_index('ix_weather_areas_city', table_name='weather_areas')
    op.drop_column('weather_areas', 'city')