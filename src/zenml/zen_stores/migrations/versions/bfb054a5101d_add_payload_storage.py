"""Add payload storage [bfb054a5101d].

Revision ID: bfb054a5101d
Revises: 8d638fcb4bd5
Create Date: 2026-09-24 15:58:32.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

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


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "blob",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("codec", sa.String(length=16), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("stored_in", sa.String(length=16), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sha256", "media_type", name="unique_blob_sha256_media_type"
        ),
    )
    op.create_index("ix_blob_stored_in", "blob", ["stored_in"])
    op.create_table(
        "blob_content",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "data",
            sa.LargeBinary().with_variant(mysql.MEDIUMBLOB, "mysql"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("sha256"),
    )

    # Nullable columns without foreign keys or indexes, so that MySQL can
    # append them without rebuilding or copying these large tables.
    for table, columns in BLOB_REFERENCE_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.add_column(
                    sa.Column(column, sa.Uuid(), nullable=True)
                )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table, columns in BLOB_REFERENCE_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in reversed(columns):
                batch_op.drop_column(column)

    op.drop_table("blob_content")
    op.drop_index("ix_blob_stored_in", table_name="blob")
    op.drop_table("blob")
