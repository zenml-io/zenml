"""Rename project to workspace. [3944116bbd56].

Revision ID: 3944116bbd56
Revises: 0.32.1
Create Date: 2023-01-24 12:54:29.192057

"""
from typing import Set

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3944116bbd56"
down_revision = "0.32.1"
branch_labels = None
depends_on = None


def _fk_constraint_name(table: str, column: str) -> str:
    """Defines the name of a foreign key constraint.

    Args:
        table: Source table name.
        column: Source column name.

    Returns:
        Name of the foreign key constraint.
    """
    return f"fk_{table}_{column}_workspace"


def _get_changed_tables() -> Set[str]:
    return {
        "artifact",
        "flavor",
        "pipeline",
        "pipeline_run",
        "schedule",
        "stack",
        "stack_component",
        "step_run",
        "team_role_assignment",
        "user_role_assignment",
    }


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    tables = _get_changed_tables()

    for table in tables:
        with op.batch_alter_table(table, schema=None) as batch_op:
            old_fk = _fk_constraint_name(table=table, column="project_id")
            batch_op.drop_constraint(old_fk, type_="foreignkey")

            batch_op.alter_column(
                column_name="project_id",
                new_column_name="workspace_id",
                existing_type=sa.CHAR(length=32),
            )

        # Once all data is moved to the new colum, create new fk
        with op.batch_alter_table(table, schema=None) as batch_op:
            new_fk = _fk_constraint_name(table=table, column="workspace_id")
            batch_op.create_foreign_key(
                new_fk,
                "workspace",
                ["workspace_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    tables = _get_changed_tables()

    for table in tables:
        with op.batch_alter_table(table, schema=None) as batch_op:
            new_fk = _fk_constraint_name(table=table, column="workspace_id")
            batch_op.drop_constraint(new_fk, type_="foreignkey")

            batch_op.alter_column(
                column_name="workspace_id",
                new_column_name="project_id",
                existing_type=sa.CHAR(length=32),
            )

        with op.batch_alter_table(table, schema=None) as batch_op:
            old_fk = _fk_constraint_name(table=table, column="project_id")
            batch_op.create_foreign_key(
                old_fk,
                "workspace",
                ["project_id"],
                ["id"],
                ondelete="CASCADE",
            )
