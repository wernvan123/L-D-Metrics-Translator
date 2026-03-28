"""Add workspace IDs to dynamic_reports

Revision ID: ws_20260301
Revises: a2c9f1e3b7a1
Create Date: 2026-03-01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'ws_20260301'
down_revision = 'add_behavioral_biases_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = set(inspector.get_table_names())

    if 'dynamic_reports' not in tables:
        return

    cols = {c['name'] for c in inspector.get_columns('dynamic_reports')}

    with op.batch_alter_table('dynamic_reports') as batch_op:
        if 'client_company_id' not in cols:
            batch_op.add_column(sa.Column('client_company_id', sa.Integer(), nullable=True))
        if 'client_engagement_id' not in cols:
            batch_op.add_column(sa.Column('client_engagement_id', sa.Integer(), nullable=True))

    # Best-effort indexes
    idx_names = {ix['name'] for ix in inspector.get_indexes('dynamic_reports')}
    if 'ix_dynamic_reports_client_company_id' not in idx_names:
        try:
            op.create_index('ix_dynamic_reports_client_company_id', 'dynamic_reports', ['client_company_id'])
        except Exception:
            pass
    if 'ix_dynamic_reports_client_engagement_id' not in idx_names:
        try:
            op.create_index('ix_dynamic_reports_client_engagement_id', 'dynamic_reports', ['client_engagement_id'])
        except Exception:
            pass


def downgrade() -> None:
    # Downgrade is best-effort; SQLite may not support dropping columns.
    try:
        op.drop_index('ix_dynamic_reports_client_engagement_id', table_name='dynamic_reports')
    except Exception:
        pass
    try:
        op.drop_index('ix_dynamic_reports_client_company_id', table_name='dynamic_reports')
    except Exception:
        pass

    try:
        with op.batch_alter_table('dynamic_reports') as batch_op:
            try:
                batch_op.drop_column('client_engagement_id')
            except Exception:
                pass
            try:
                batch_op.drop_column('client_company_id')
            except Exception:
                pass
    except Exception:
        pass
