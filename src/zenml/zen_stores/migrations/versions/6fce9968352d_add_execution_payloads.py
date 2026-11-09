"""Add execution payloads [6fce9968352d].

Revision ID: 6fce9968352d
Revises: 8d638fcb4bd5
Create Date: 2026-10-19 22:32:17.741748

"""

from datetime import datetime, timezone
from typing import List

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "6fce9968352d"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None

PAYLOAD_REFERENCE_COLUMNS = {
    "pipeline_snapshot": [
        "pipeline_configuration_payload_id",
        "client_environment_payload_id",
        "pipeline_spec_payload_id",
        "source_code_payload_id",
    ],
    "step_configuration": ["config_payload_id"],
    "step_run": ["source_code_payload_id", "docstring_payload_id"],
    "pipeline_run": ["orchestrator_environment_payload_id"],
}


def _add_columns(
    dialect: sa.Dialect,
    table: str,
    columns: List[sa.Column],  # type: ignore[type-arg]
) -> None:
    """Add nullable columns to a table.

    Args:
        dialect: The dialect of the database.
        table: The table.
        columns: The columns to add.
    """
    if dialect.name == "mysql":
        # MySQL allows 64 instant column changes per table before it has to
        # copy the table, and counts one per statement. Batch mode issues one
        # statement per column, so each table gets a single statement here.
        op.execute(
            f"ALTER TABLE `{table}` "
            + ", ".join(
                f"ADD COLUMN `{column.name}` "
                f"{column.type.compile(dialect=dialect)} NULL"
                for column in columns
            )
        )
    else:
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.add_column(column)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    dialect = op.get_bind().dialect
    op.create_table(
        "execution_payload",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column(
            "value",
            sa.String(length=16777215).with_variant(
                mysql.MEDIUMTEXT(), "mysql"
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("sha256"),
    )
    for table, columns in PAYLOAD_REFERENCE_COLUMNS.items():
        _add_columns(
            dialect,
            table,
            [
                sa.Column(column, sa.String(length=64), nullable=True)
                for column in columns
            ],
        )

    # Off for databases that older releases, which only read inline values,
    # may still use during a rolling upgrade. A later release moves the
    # payloads of existing rows and then turns it on.
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payload_references_enabled",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        # The release that turns references on waits a delay after this, to
        # give a rolling upgrade time to replace the processes that cannot
        # read them. The delay does not check which releases still run.
        batch_op.add_column(
            sa.Column("execution_payloads_added", sa.DateTime(), nullable=True)
        )
    server_settings = sa.table(
        "server_settings",
        sa.column("execution_payloads_added", sa.DateTime),
        sa.column("payload_references_enabled", sa.Boolean),
    )
    op.execute(
        server_settings.update().values(
            execution_payloads_added=datetime.now(timezone.utc).replace(
                tzinfo=None
            ),
            # A SQLite database is only used by the process that migrates it.
            payload_references_enabled=dialect.name == "sqlite",
        )
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        RuntimeError: If execution payloads were stored, since dropping them
            would lose the values that rows reference.
    """
    if (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM execution_payload LIMIT 1"))
        .first()
    ):
        raise RuntimeError(
            "Execution payloads are stored, and this downgrade would drop "
            "them. Only databases without stored execution "
            "payloads can be downgraded below this revision."
        )
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.drop_column("execution_payloads_added")
        batch_op.drop_column("payload_references_enabled")
    for table, columns in PAYLOAD_REFERENCE_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in reversed(columns):
                batch_op.drop_column(column)
    op.drop_table("execution_payload")
