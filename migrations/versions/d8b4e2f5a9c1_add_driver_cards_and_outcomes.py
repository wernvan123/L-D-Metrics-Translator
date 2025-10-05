"""Add driver card refs to KSAOs and outcomes table

Revision ID: d8b4e2f5a9c1
Revises: 92e8a3144dc5
Create Date: 2025-10-05 15:42:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8b4e2f5a9c1'
down_revision = '92e8a3144dc5'
branch_labels = None
depends_on = None


def upgrade():
    # Add driver_card_id columns to existing KSAO tables
    for table_name, fk_name, include_target in (
        ('role_knowledge', 'fk_role_knowledge_driver_card', True),
        ('role_skills', 'fk_role_skills_driver_card', True),
        ('role_abilities', 'fk_role_abilities_driver_card', True),
        ('role_other_requirements', 'fk_role_other_requirements_driver_card', False),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column('driver_card_id', sa.Integer(), nullable=True))
            if include_target:
                batch_op.add_column(sa.Column('target_level', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                fk_name,
                'metrics',
                ['driver_card_id'],
                ['id'],
                ondelete='SET NULL',
            )

    # Create role_outcomes table
    op.create_table(
        'role_outcomes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('driver_card_id', sa.Integer(), sa.ForeignKey('metrics.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_level', sa.Integer(), nullable=True),
    )
    op.create_index('ix_role_outcomes_driver_card_id', 'role_outcomes', ['driver_card_id'])


def downgrade():
    op.drop_index('ix_role_outcomes_driver_card_id', table_name='role_outcomes')
    op.drop_table('role_outcomes')

    for table_name, fk_name, include_target in (
        ('role_other_requirements', 'fk_role_other_requirements_driver_card', False),
        ('role_abilities', 'fk_role_abilities_driver_card', True),
        ('role_skills', 'fk_role_skills_driver_card', True),
        ('role_knowledge', 'fk_role_knowledge_driver_card', True),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(fk_name, type_='foreignkey')
            batch_op.drop_column('driver_card_id')
            if include_target:
                batch_op.drop_column('target_level')
