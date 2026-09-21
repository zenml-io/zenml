"""Add execution archive [c3f5a9e1d7b2].

Revision ID: c3f5a9e1d7b2
Revises: 9f2b8c7d6e5a
Create Date: 2026-09-11 10:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "c3f5a9e1d7b2"
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
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("uri", sa.TEXT(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "content_hash",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_archive_bundle_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["pipeline_run.id"],
            name="fk_archive_bundle_run_id_pipeline_run",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_archive_bundle_run_id", "archive_bundle", ["run_id"])
    with op.batch_alter_table("server_settings") as batch_op:
        batch_op.add_column(
            sa.Column("retention_state", sa.TEXT(), nullable=True)
        )

    # The marker columns carry no foreign key and no index on purpose. These
    # are among the largest tables, and nothing looks rows up by marker alone:
    # reads test it on rows they already found, and a bundle's run is reached
    # through `archive_bundle.run_id`.
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

    # The one index retention does need: the sweep walks every project's runs
    # in this order, so without it each pass filesorts the whole table. MySQL
    # builds secondary indexes online, but on a large `pipeline_run` this
    # still takes time. Targeted archives page by `created` instead, which
    # the existing project and pipeline indexes already serve.
    op.create_index(
        "ix_pipeline_run_end_time_id", "pipeline_run", ["end_time", "id"]
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        RuntimeError: Detail has already been archived, so dropping the
            markers would leave those rows empty and unlocatable.
    """
    archived = (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM archive_bundle LIMIT 1"))
        .first()
    )
    if archived is not None:
        raise RuntimeError(
            "Execution detail has been archived on this server. Downgrading "
            "would drop the `archive_bundle` table and the markers pointing "
            "at it. Downgrading after archiving is unsupported, including "
            "after restoring runs: archive catalog records are retained. "
            "Keep the current database schema."
        )

    op.drop_index("ix_pipeline_run_end_time_id", table_name="pipeline_run")
    for table in ARCHIVABLE_TABLES:
        if table == "step_run":
            op.drop_column(table, "substitutions")
            op.drop_column(table, "step_type")
        op.drop_column(table, "archive_bundle_id")

    op.drop_table("archive_bundle")
    # Native DROP avoids rebuilding the table and cascading dependent rows.
    op.drop_column("server_settings", "retention_state")
