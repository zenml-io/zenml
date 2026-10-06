"""Add payload storage [bfb054a5101d].

Revision ID: bfb054a5101d
Revises: 8d638fcb4bd5
Create Date: 2026-09-24 15:58:32.000000

"""

from typing import List

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bfb054a5101d"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None

BLOB_REFERENCE_COLUMNS = {
    "pipeline_snapshot": [
        "pipeline_configuration_blob_id",
        "client_environment_blob_id",
        "pipeline_spec_blob_id",
        "source_code_blob_id",
    ],
    "step_configuration": ["config_blob_id"],
    "step_run": ["source_code_blob_id", "docstring_blob_id"],
    "pipeline_run": ["orchestrator_environment_blob_id"],
}


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
    op.create_table(
        "payload_blob",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("codec", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "location_fingerprint", sa.String(length=16), nullable=False
        ),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256", name="unique_payload_blob_sha256"),
    )
    _add_columns(
        "server_settings",
        [sa.Column("payload_location_fingerprint", sa.String(length=16))],
    )

    for table, columns in BLOB_REFERENCE_COLUMNS.items():
        _add_columns(
            table,
            [
                sa.Column(column, sa.Uuid(), nullable=True)
                for column in columns
            ],
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        RuntimeError: If payloads were offloaded, since dropping the reference
            columns would lose which blob each row points to.
    """
    if (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM payload_blob LIMIT 1"))
        .first()
    ):
        raise RuntimeError(
            "Execution payloads were offloaded to object storage, and this "
            "downgrade would lose which blob each row references. Only "
            "databases without offloaded payloads can be downgraded below "
            "this revision."
        )
    for table, columns in BLOB_REFERENCE_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in reversed(columns):
                batch_op.drop_column(column)
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.drop_column("payload_location_fingerprint")

    op.drop_table("payload_blob")
