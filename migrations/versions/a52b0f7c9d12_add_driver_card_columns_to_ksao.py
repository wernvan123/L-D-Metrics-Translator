"""Add driver card references to role KSAO tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a52b0f7c9d12"
down_revision = "rp_20250915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("role_knowledge", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    op.add_column("role_knowledge", sa.Column("target_level", sa.Integer(), nullable=True))
    op.add_column("role_skills", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    op.add_column("role_skills", sa.Column("target_level", sa.Integer(), nullable=True))
    op.add_column("role_abilities", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    op.add_column("role_abilities", sa.Column("target_level", sa.Integer(), nullable=True))
    op.add_column("role_other_requirements", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    op.add_column("role_outcomes", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    op.add_column("role_outcomes", sa.Column("target_level", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("role_outcomes", "target_level")
    op.drop_column("role_outcomes", "driver_card_id")
    op.drop_column("role_other_requirements", "driver_card_id")
    op.drop_column("role_abilities", "target_level")
    op.drop_column("role_abilities", "driver_card_id")
    op.drop_column("role_skills", "target_level")
    op.drop_column("role_skills", "driver_card_id")
    op.drop_column("role_knowledge", "target_level")
    op.drop_column("role_knowledge", "driver_card_id")
