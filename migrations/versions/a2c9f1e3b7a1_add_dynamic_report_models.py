"""Add dynamic report models (templates, reports, analytics)

Revision ID: a2c9f1e3b7a1
Revises: f541db0413b2
Create Date: 2025-08-26 16:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'a2c9f1e3b7a1'
down_revision = 'f541db0413b2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = set(inspector.get_table_names())

    # report_templates
    if 'report_templates' not in tables:
        op.create_table(
            'report_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('template_type', sa.String(length=50), nullable=False),
            sa.Column('sections', sa.Text(), nullable=True),
            sa.Column('styling', sa.Text(), nullable=True),
            sa.Column('created_by', sa.String(length=120), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_date', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_report_templates_template_type', 'report_templates', ['template_type'])
    else:
        cols = {c['name'] for c in inspector.get_columns('report_templates')}
        if 'created_by' not in cols:
            op.add_column('report_templates', sa.Column('created_by', sa.String(length=120), nullable=True))
        # ensure index exists
        idx_names = {ix['name'] for ix in inspector.get_indexes('report_templates')}
        if 'ix_report_templates_template_type' not in idx_names:
            op.create_index('ix_report_templates_template_type', 'report_templates', ['template_type'])

    # dynamic_reports
    if 'dynamic_reports' not in tables:
        op.create_table(
            'dynamic_reports',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('title', sa.String(length=300), nullable=False),
            sa.Column('template_id', sa.Integer(), sa.ForeignKey('report_templates.id'), nullable=False),
            sa.Column('session_id', sa.String(length=255), nullable=False),
            sa.Column('selected_outcomes', sa.Text(), nullable=True),
            sa.Column('selected_metrics', sa.Text(), nullable=True),
            sa.Column('ai_recommendations', sa.Text(), nullable=True),
            sa.Column('generation_context', sa.Text(), nullable=True),
            sa.Column('executive_summary', sa.Text(), nullable=True),
            sa.Column('strategy_context', sa.Text(), nullable=True),
            sa.Column('metric_analysis', sa.Text(), nullable=True),
            sa.Column('ai_insights', sa.Text(), nullable=True),
            sa.Column('implementation_roadmap', sa.Text(), nullable=True),
            sa.Column('success_metrics', sa.Text(), nullable=True),
            sa.Column('appendices', sa.Text(), nullable=True),
            sa.Column('generation_status', sa.String(length=50), nullable=False, server_default='queued'),
            sa.Column('generation_progress', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('estimated_pages', sa.Integer(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('pdf_path', sa.String(length=500), nullable=True),
            sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_date', sa.DateTime(), nullable=False),
            sa.Column('generated_date', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_dynamic_reports_session_id', 'dynamic_reports', ['session_id'])
    else:
        cols = inspector.get_columns('dynamic_reports')
        colmap = {c['name']: c for c in cols}
        # Ensure index exists
        idx_names = {ix['name'] for ix in inspector.get_indexes('dynamic_reports')}
        if 'ix_dynamic_reports_session_id' not in idx_names:
            op.create_index('ix_dynamic_reports_session_id', 'dynamic_reports', ['session_id'])
        # Attempt to alter session_id type if not String and backend supports it
        try:
            session_col = colmap.get('session_id')
            if session_col is not None:
                # Only attempt if not already VARCHAR/STRING
                if not isinstance(session_col.get('type'), sa.String):
                    op.alter_column('dynamic_reports', 'session_id', type_=sa.String(length=255))
        except Exception:
            # On SQLite, altering types is limited; skip safely
            pass

    # report_analytics
    if 'report_analytics' not in tables:
        op.create_table(
            'report_analytics',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('report_id', sa.Integer(), sa.ForeignKey('dynamic_reports.id'), nullable=False),
            sa.Column('outcome_distribution', sa.Text(), nullable=True),
            sa.Column('metric_type_distribution', sa.Text(), nullable=True),
            sa.Column('ai_recommendation_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('complexity_score', sa.Float(), nullable=True),
            sa.Column('created_date', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_report_analytics_report_id', 'report_analytics', ['report_id'])


def downgrade():
    op.drop_index('ix_report_analytics_report_id', table_name='report_analytics')
    op.drop_table('report_analytics')

    op.drop_index('ix_dynamic_reports_session_id', table_name='dynamic_reports')
    op.drop_table('dynamic_reports')

    op.drop_index('ix_report_templates_template_type', table_name='report_templates')
    op.drop_table('report_templates')
