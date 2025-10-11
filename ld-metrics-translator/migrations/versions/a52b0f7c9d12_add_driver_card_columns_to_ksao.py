"""Add driver card references to role KSAO tables.

Revision ID: a52b0f7c9d12
Revises: rp_20250915
Create Date: 2025-10-11 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a52b0f7c9d12"
down_revision = "rp_20250915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def add_column_if_missing(table: str, column: sa.Column) -> None:
        existing = {col["name"] for col in inspector.get_columns(table)}
        if column.name not in existing:
            op.add_column(table, column)

    add_column_if_missing("role_knowledge", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    add_column_if_missing("role_knowledge", sa.Column("target_level", sa.Integer(), nullable=True))

    add_column_if_missing("role_skills", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    add_column_if_missing("role_skills", sa.Column("target_level", sa.Integer(), nullable=True))

    add_column_if_missing("role_abilities", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    add_column_if_missing("role_abilities", sa.Column("target_level", sa.Integer(), nullable=True))

    add_column_if_missing("role_other_requirements", sa.Column("driver_card_id", sa.Integer(), nullable=True))

    add_column_if_missing("role_outcomes", sa.Column("driver_card_id", sa.Integer(), nullable=True))
    add_column_if_missing("role_outcomes", sa.Column("target_level", sa.Integer(), nullable=True))

    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_role_knowledge_driver_card",
            "role_knowledge",
            "metrics",
            ["driver_card_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_role_skills_driver_card",
            "role_skills",
            "metrics",
            ["driver_card_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_role_abilities_driver_card",
            "role_abilities",
            "metrics",
            ["driver_card_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_role_other_requirements_driver_card",
            "role_other_requirements",
            "metrics",
            ["driver_card_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_role_outcomes_driver_card",
            "role_outcomes",
            "metrics",
            ["driver_card_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def drop_column_if_exists(table: str, column_name: str) -> None:
        existing = {col["name"] for col in inspector.get_columns(table)}
        if column_name in existing:
            op.drop_column(table, column_name)

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_role_outcomes_driver_card", "role_outcomes", type_="foreignkey")
    drop_column_if_exists("role_outcomes", "target_level")
    drop_column_if_exists("role_outcomes", "driver_card_id")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_role_other_requirements_driver_card", "role_other_requirements", type_="foreignkey")
    drop_column_if_exists("role_other_requirements", "driver_card_id")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_role_abilities_driver_card", "role_abilities", type_="foreignkey")
    drop_column_if_exists("role_abilities", "target_level")
    drop_column_if_exists("role_abilities", "driver_card_id")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_role_skills_driver_card", "role_skills", type_="foreignkey")
    drop_column_if_exists("role_skills", "target_level")
    drop_column_if_exists("role_skills", "driver_card_id")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_role_knowledge_driver_card", "role_knowledge", type_="foreignkey")
    drop_column_if_exists("role_knowledge", "target_level")
    drop_column_if_exists("role_knowledge", "driver_card_id")
