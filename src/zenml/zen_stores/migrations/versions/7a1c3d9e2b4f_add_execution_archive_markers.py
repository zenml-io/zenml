"""Add execution archive markers [7a1c3d9e2b4f].

Revision ID: 7a1c3d9e2b4f
Revises: 9f2b8c7d6e5a
Create Date: 2026-09-07 10:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "7a1c3d9e2b4f"
down_revision = "9f2b8c7d6e5a"
branch_labels = None
depends_on = None


ARCHIVABLE_TABLES = (
    "pipeline_run",
    "step_run",
    "pipeline_snapshot",
)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "archive_bundle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("root_run_id", sa.Uuid(), nullable=True),
        sa.Column("uri", sa.TEXT(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("row_counts", sa.TEXT(), nullable=False),
        sa.Column(
            "manifest_hash",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column(
            "schema_revision",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "status", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "claimed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("status_reason", sa.TEXT(), nullable=True),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_archive_bundle_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["root_run_id"],
            ["pipeline_run.id"],
            name="fk_archive_bundle_root_run_id_pipeline_run",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # The marker columns carry no foreign key and no index on purpose: these
    # are among the largest tables, so index and constraint rollout needs its
    # own migration timing. The server default on `retain` lets older
    # server replicas keep inserting runs during a rolling upgrade.
    for table in ARCHIVABLE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("archived_at", sa.DateTime(), nullable=True)
            )
            batch_op.add_column(
                sa.Column("archive_bundle_id", sa.Uuid(), nullable=True)
            )
            if table == "step_run":
                batch_op.add_column(
                    sa.Column(
                        "step_type",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=True,
                    )
                )
                batch_op.add_column(
                    sa.Column("substitutions", sa.TEXT(), nullable=True)
                )
            if table == "pipeline_run":
                batch_op.add_column(
                    sa.Column(
                        "retain",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table in ARCHIVABLE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            if table == "step_run":
                batch_op.drop_column("substitutions")
                batch_op.drop_column("step_type")
            if table == "pipeline_run":
                batch_op.drop_column("retain")
            batch_op.drop_column("archive_bundle_id")
            batch_op.drop_column("archived_at")

    op.drop_table("archive_bundle")
