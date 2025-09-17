"""add role profiling (KSAO) tables

Revision ID: rp_20250915
Revises: mrg_20250911
Create Date: 2025-09-15 14:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rp_20250915'
down_revision = 'mrg_20250911'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # role_profiles
    op.create_table(
        'role_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('department', sa.String(length=200)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_date', sa.DateTime(), nullable=False),
    )

    # role_knowledge
    op.create_table(
        'role_knowledge',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text()),
    )
    op.create_index('ix_role_knowledge_role_profile_id', 'role_knowledge', ['role_profile_id'])

    # role_skills
    op.create_table(
        'role_skills',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text()),
    )
    op.create_index('ix_role_skills_role_profile_id', 'role_skills', ['role_profile_id'])

    # role_abilities
    op.create_table(
        'role_abilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text()),
    )
    op.create_index('ix_role_abilities_role_profile_id', 'role_abilities', ['role_profile_id'])

    # role_other_requirements
    op.create_table(
        'role_other_requirements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text()),
    )
    op.create_index('ix_role_other_requirements_role_profile_id', 'role_other_requirements', ['role_profile_id'])

    # role_competency_targets
    op.create_table(
        'role_competency_targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_id', sa.Integer(), sa.ForeignKey('competencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_level', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('weight', sa.Float(), server_default='1.0'),
    )
    op.create_index('ix_role_competency_targets_role_profile_id', 'role_competency_targets', ['role_profile_id'])
    op.create_index('ix_role_competency_targets_competency_id', 'role_competency_targets', ['competency_id'])

    # role_assignments
    op.create_table(
        'role_assignments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_profile_id', sa.Integer(), sa.ForeignKey('role_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('person_identifier', sa.String(length=255), nullable=False),
        sa.Column('assigned_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )
    op.create_index('ix_role_assignments_role_profile_id', 'role_assignments', ['role_profile_id'])
    op.create_index('ix_role_assignments_person_identifier', 'role_assignments', ['person_identifier'])


def downgrade() -> None:
    # drop in reverse order of FKs
    op.drop_index('ix_role_assignments_person_identifier', table_name='role_assignments')
    op.drop_index('ix_role_assignments_role_profile_id', table_name='role_assignments')
    op.drop_table('role_assignments')

    op.drop_index('ix_role_competency_targets_competency_id', table_name='role_competency_targets')
    op.drop_index('ix_role_competency_targets_role_profile_id', table_name='role_competency_targets')
    op.drop_table('role_competency_targets')

    op.drop_index('ix_role_other_requirements_role_profile_id', table_name='role_other_requirements')
    op.drop_table('role_other_requirements')

    op.drop_index('ix_role_abilities_role_profile_id', table_name='role_abilities')
    op.drop_table('role_abilities')

    op.drop_index('ix_role_skills_role_profile_id', table_name='role_skills')
    op.drop_table('role_skills')

    op.drop_index('ix_role_knowledge_role_profile_id', table_name='role_knowledge')
    op.drop_table('role_knowledge')

    op.drop_table('role_profiles')
