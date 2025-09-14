"""add driver card fields to metrics

Revision ID: c3a1b2c4d5e6
Revises: b00debb5bc67
Create Date: 2025-09-11 17:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3a1b2c4d5e6'
down_revision = 'b00debb5bc67'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('metrics') as batch_op:
        batch_op.add_column(sa.Column('identifier_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('driver_chain', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('metrics') as batch_op:
        batch_op.drop_column('driver_chain')
        batch_op.drop_column('identifier_type')
