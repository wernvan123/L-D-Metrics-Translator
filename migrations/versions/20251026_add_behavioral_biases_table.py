"""add behavioral biases table

Revision ID: add_behavioral_biases_table
Revises: e1f7d3a2c4b5
Create Date: 2025-10-26 13:53:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_behavioral_biases_table'
down_revision = 'e1f7d3a2c4b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'behavioral_biases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False, unique=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('detailed_description', sa.Text(), nullable=True),
        sa.Column('countermeasures', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('trigger_keywords', sa.Text(), nullable=True),
        sa.Column('model_framework', sa.String(length=255), nullable=True),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_behavioral_biases_slug', 'behavioral_biases', ['slug'], unique=True)
    op.create_index('ix_behavioral_biases_is_active', 'behavioral_biases', ['is_active'])
    op.create_index('ix_behavioral_biases_model_framework', 'behavioral_biases', ['model_framework'])


def downgrade() -> None:
    op.drop_index('ix_behavioral_biases_model_framework', table_name='behavioral_biases')
    op.drop_index('ix_behavioral_biases_is_active', table_name='behavioral_biases')
    op.drop_index('ix_behavioral_biases_slug', table_name='behavioral_biases')
    op.drop_table('behavioral_biases')
