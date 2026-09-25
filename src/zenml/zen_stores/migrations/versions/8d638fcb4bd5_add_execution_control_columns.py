"""Add execution control columns [8d638fcb4bd5].

Revision ID: 8d638fcb4bd5
Revises: c7d4e8a2b5f1
Create Date: 2026-09-24 00:20:46.000000

"""

from typing import List

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "8d638fcb4bd5"
down_revision = "c7d4e8a2b5f1"
branch_labels = None
depends_on = None

# JSON values without a practical size bound use the same type as the
# configuration columns they are derived from.
JSON_TEXT_TYPE = sa.String(length=16777215).with_variant(
    mysql.MEDIUMTEXT, "mysql"
)


def _add_columns(table: str, columns: List[sa.Column]) -> None:  # type: ignore[type-arg]
    """Add nullable columns to a table.

    Args:
        table: The table.
        columns: The columns to add.
    """
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # MySQL allows 64 instant column changes per table before it has to
        # copy the table, and counts one per statement. Batch mode issues one
        # statement per column, so each table gets a single statement here.
        op.execute(
            f"ALTER TABLE `{table}` "
            + ", ".join(
                f"ADD COLUMN `{column.name}` "
                f"{column.type.compile(dialect=bind.dialect)} NULL"
                for column in columns
            )
        )
    else:
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.add_column(column)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # All columns are nullable and appended, so MySQL can add them without
    # rebuilding these large tables. Existing rows keep NULL values and are
    # read through the previous JSON-parsing code path.
    _add_columns(
        "pipeline_snapshot",
        [
            sa.Column(
                "execution_mode",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
            sa.Column("enable_heartbeat", sa.Boolean(), nullable=True),
        ],
    )
    _add_columns(
        "step_configuration",
        [sa.Column("upstream_steps", JSON_TEXT_TYPE, nullable=True)],
    )
    _add_columns(
        "step_run",
        [
            sa.Column(
                "step_type",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
            sa.Column("substitutions", JSON_TEXT_TYPE, nullable=True),
        ],
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("substitutions")
        batch_op.drop_column("step_type")

    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.drop_column("upstream_steps")

    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.drop_column("enable_heartbeat")
        batch_op.drop_column("execution_mode")
