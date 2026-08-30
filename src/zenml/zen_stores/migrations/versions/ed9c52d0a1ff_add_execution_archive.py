"""Add execution archive [ed9c52d0a1ff].

Revision ID: ed9c52d0a1ff
Revises: 0.96.3
Create Date: 2026-08-29 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "ed9c52d0a1ff"
down_revision = "0.96.3"
branch_labels = None
depends_on = None

_MEDIUMTEXT = sa.String(length=16777215).with_variant(
    mysql.MEDIUMTEXT, "mysql"
)
_AUTHORITATIVE_STATES = ("compacting", "cold", "restoring")


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "execution_archive_storage_target",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("flavor", sa.String(length=255), nullable=False),
        sa.Column("flavor_source", sa.TEXT(), nullable=False),
        sa.Column("configuration", _MEDIUMTEXT, nullable=False),
        sa.Column("path_prefix", sa.String(length=512), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "digest", name="unique_execution_archive_storage_target_digest"
        ),
    )

    op.create_table(
        "execution_archive",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("root_run_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("storage_target_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("manifest_stored_bytes", sa.BigInteger(), nullable=True),
        sa.Column("execution_sha256", sa.String(length=64), nullable=True),
        sa.Column("execution_stored_bytes", sa.BigInteger(), nullable=True),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=True),
        sa.Column("snapshot_stored_bytes", sa.BigInteger(), nullable=True),
        sa.Column("stored_bytes", sa.BigInteger(), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("owner_expires_at", sa.DateTime(), nullable=True),
        sa.Column("committed_at", sa.DateTime(), nullable=True),
        sa.Column("compacted_at", sa.DateTime(), nullable=True),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_execution_archive_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["storage_target_id"],
            ["execution_archive_storage_target.id"],
            name="fk_execution_archive_storage_target_id_storage_target",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "root_run_id",
            "generation",
            name="unique_execution_archive_root_generation",
        ),
    )
    op.create_index(
        "ix_execution_archive_project_id_state",
        "execution_archive",
        ["project_id", "state"],
        unique=False,
    )

    # Authority marker: set on the snapshots of a family while an archive is
    # authoritative for their payload. Adding a nullable column is an
    # instant, metadata-only change; the payload columns stay NOT NULL.
    with op.batch_alter_table("pipeline_snapshot") as batch_op:
        batch_op.add_column(
            sa.Column("execution_archive_id", sa.Uuid(), nullable=True)
        )

    # Step type and substitutions are needed by unhydrated step listings and
    # used to live only inside the step configuration. Existing rows are not
    # backfilled: readers derive both from the configuration while it is
    # still hot, and compaction stores them before it clears the
    # configuration. A backfill would scan the largest table for no gain.
    with op.batch_alter_table("step_run") as batch_op:
        batch_op.add_column(
            sa.Column("step_type", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("substitutions", sa.TEXT(), nullable=True)
        )

    # Candidate discovery filters completed root runs by their last update.
    # This is the one change that is not instant: MySQL builds the index
    # online, in time proportional to the size of `pipeline_run`.
    op.create_index(
        "ix_pipeline_run_status_updated",
        "pipeline_run",
        ["status", "updated"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        RuntimeError: If an archive is still authoritative for hot rows,
            whose payload the previous revision cannot read.
    """
    archive = sa.table(
        "execution_archive", sa.column("state", sa.String(length=32))
    )
    authoritative = (
        op.get_bind()
        .execute(
            sa.select(sa.func.count())
            .select_from(archive)
            .where(archive.c.state.in_(_AUTHORITATIVE_STATES))
        )
        .scalar_one()
    )
    if authoritative:
        raise RuntimeError(
            "Restore every compacted execution archive before downgrading."
        )

    op.drop_index("ix_pipeline_run_status_updated", table_name="pipeline_run")

    with op.batch_alter_table("step_run") as batch_op:
        batch_op.drop_column("substitutions")
        batch_op.drop_column("step_type")

    with op.batch_alter_table("pipeline_snapshot") as batch_op:
        batch_op.drop_column("execution_archive_id")

    op.drop_index(
        "ix_execution_archive_project_id_state", table_name="execution_archive"
    )
    op.drop_table("execution_archive")
    op.drop_table("execution_archive_storage_target")
