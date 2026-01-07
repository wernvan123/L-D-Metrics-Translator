"""add knowledge base tables for tiered resources

Revision ID: e1f7d3a2c4b5
Revises: rp_20250915
Create Date: 2025-10-14 17:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f7d3a2c4b5'
down_revision = 'rp_20250915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'knowledge_categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'knowledge_resources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('heading', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tier', sa.String(length=10), nullable=False),
        sa.Column('tags', sa.String(length=255), nullable=True),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('context', sa.String(length=100), nullable=True),
        sa.Column('seq_id', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('knowledge_categories.id'), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_resources_category_id', 'knowledge_resources', ['category_id'])
    op.create_index('ix_knowledge_resources_tier', 'knowledge_resources', ['tier'])
    op.create_index('ix_knowledge_resources_context', 'knowledge_resources', ['context'])


def downgrade() -> None:
    op.drop_index('ix_knowledge_resources_context', table_name='knowledge_resources')
    op.drop_index('ix_knowledge_resources_tier', table_name='knowledge_resources')
    op.drop_index('ix_knowledge_resources_category_id', table_name='knowledge_resources')
    op.drop_table('knowledge_resources')
    op.drop_table('knowledge_categories')
