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
        sa.Column("active_root_id", sa.Uuid(), nullable=True),
        sa.Column(
            "claim_token", sa.BigInteger(), nullable=False, server_default="1"
        ),
        sa.Column("claim_expires_at", sa.DateTime(), nullable=True),
        sa.Column("uri", sa.TEXT(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "manifest_hash",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("format_version", sa.Integer(), nullable=False),
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

    op.create_index(
        "ix_archive_bundle_active_root_id",
        "archive_bundle",
        ["active_root_id"],
        unique=True,
    )
    op.create_index(
        "ix_archive_bundle_root_created_id",
        "archive_bundle",
        ["root_run_id", "created", "id"],
    )
    with op.batch_alter_table("project") as batch_op:
        batch_op.add_column(
            sa.Column("retention_settings", sa.TEXT(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("retention_state", sa.TEXT(), nullable=True)
        )

    # The marker columns carry no foreign key and no index on purpose: these
    # are among the largest tables, so index and constraint rollout needs its
    # own migration timing. The server default on `retain` lets older
    # server replicas keep inserting runs during a rolling upgrade.
    for table in ARCHIVABLE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
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
                        # A literal keeps SQLite on native ADD COLUMN; an
                        # expression forces recreation and can cascade-delete
                        # referencing rows on FK-enabled migration connections.
                        server_default="0",
                    )
                )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table in ARCHIVABLE_TABLES:
        if table == "step_run":
            op.drop_column(table, "substitutions")
            op.drop_column(table, "step_type")
        if table == "pipeline_run":
            op.drop_column(table, "retain")
        op.drop_column(table, "archive_bundle_id")

    op.drop_table("archive_bundle")
    # Native DROP avoids rebuilding project and cascading its dependent rows.
    op.drop_column("project", "retention_state")
    op.drop_column("project", "retention_settings")
