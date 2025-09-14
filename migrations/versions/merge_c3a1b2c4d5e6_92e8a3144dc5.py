"""merge heads c3a1b2c4d5e6 and 92e8a3144dc5

Revision ID: mrg_20250911
Revises: c3a1b2c4d5e6, 92e8a3144dc5
Create Date: 2025-09-11 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'mrg_20250911'
down_revision = ('c3a1b2c4d5e6', '92e8a3144dc5')
branch_labels = None
depends_on = None

def upgrade() -> None:
    # No-op merge migration
    pass


def downgrade() -> None:
    # No-op merge migration
    pass
