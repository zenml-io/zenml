"""Add the execution archive foundation.

Revision ID: ed9c52d0a1ff
Revises: 0.96.3
Create Date: 2026-08-29 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ed9c52d0a1ff"
down_revision = "0.96.3"
branch_labels = None
depends_on = None

_AUTHORITATIVE_STATES = ("compacting", "cold", "restoring")


def upgrade() -> None:
    """Create the inert archive catalog and conversion/fencing columns."""
    op.create_table(
        "execution_archive",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        # Logical identifiers deliberately outlive project/run rows.
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("root_run_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "storage_target_digest", sa.String(length=64), nullable=False
        ),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("object_sha256", sa.String(length=64), nullable=True),
        sa.Column("object_stored_bytes", sa.BigInteger(), nullable=True),
        sa.Column("object_decoded_bytes", sa.BigInteger(), nullable=True),
        sa.Column("source_bytes", sa.BigInteger(), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        # Every acquisition increments this value. Later archive operations
        # use it to fence workers whose lease expired and was taken over.
        sa.Column(
            "claim_token",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("owner_expires_at", sa.DateTime(), nullable=True),
        sa.Column("committed_at", sa.DateTime(), nullable=True),
        sa.Column("compacted_at", sa.DateTime(), nullable=True),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.Column("purge_pending_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
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
    op.create_index(
        "ix_execution_archive_purge_pending_at",
        "execution_archive",
        ["purge_pending_at"],
        unique=False,
    )
    op.create_index(
        "ix_execution_archive_state_updated_id",
        "execution_archive",
        ["state", "updated", "id"],
        unique=False,
    )

    # Both nullable marker columns and the step list projections are instant
    # ADD COLUMN operations on supported MySQL 8 versions. Payload columns keep
    # their existing NOT NULL constraints and are compacted to typed markers.
    with op.batch_alter_table("pipeline_run") as batch_op:
        batch_op.add_column(
            sa.Column("execution_archive_id", sa.Uuid(), nullable=True)
        )

    with op.batch_alter_table("server_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_archive_target_digest",
                sa.String(length=64),
                nullable=True,
            )
        )

    with op.batch_alter_table("pipeline_snapshot") as batch_op:
        batch_op.add_column(
            sa.Column("execution_archive_id", sa.Uuid(), nullable=True)
        )

    with op.batch_alter_table("step_run") as batch_op:
        batch_op.add_column(
            sa.Column("step_type", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("substitutions", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    """Remove the foundation if no archive owns SQL payload.

    Raises:
        RuntimeError: If compacted payload requires the archive-aware schema.
    """
    archive = sa.table(
        "execution_archive",
        sa.column("state", sa.String(length=32)),
        sa.column("object_key", sa.Text()),
        sa.column("compacted_at", sa.DateTime()),
        sa.column("restored_at", sa.DateTime()),
    )
    unsafe = (
        op.get_bind()
        .execute(
            sa.select(sa.func.count())
            .select_from(archive)
            .where(
                sa.or_(
                    archive.c.object_key.is_not(None),
                    archive.c.state.in_(_AUTHORITATIVE_STATES),
                    sa.and_(
                        archive.c.state == "corrupt",
                        archive.c.compacted_at.is_not(None),
                        archive.c.restored_at.is_(None),
                    ),
                )
            )
        )
        .scalar_one()
    )
    if unsafe:
        raise RuntimeError(
            "Restore every compacted execution archive and purge every "
            "stored generation before removing the archive foundation."
        )

    with op.batch_alter_table("step_run") as batch_op:
        batch_op.drop_column("substitutions")
        batch_op.drop_column("step_type")

    with op.batch_alter_table("pipeline_snapshot") as batch_op:
        batch_op.drop_column("execution_archive_id")

    with op.batch_alter_table("pipeline_run") as batch_op:
        batch_op.drop_column("execution_archive_id")

    with op.batch_alter_table("server_settings") as batch_op:
        batch_op.drop_column("execution_archive_target_digest")

    op.drop_index(
        "ix_execution_archive_state_updated_id",
        table_name="execution_archive",
    )

    op.drop_index(
        "ix_execution_archive_purge_pending_at",
        table_name="execution_archive",
    )
    op.drop_index(
        "ix_execution_archive_project_id_state",
        table_name="execution_archive",
    )
    op.drop_table("execution_archive")
