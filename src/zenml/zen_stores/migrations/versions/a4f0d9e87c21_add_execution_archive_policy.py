"""Add workspace execution archive policy and coordination.

Revision ID: a4f0d9e87c21
Revises: ed9c52d0a1ff
Create Date: 2026-08-31 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4f0d9e87c21"
down_revision = "ed9c52d0a1ff"
branch_labels = None
depends_on = None

_AUTHORITATIVE_STATES = ("compacting", "cold", "restoring")


def upgrade() -> None:
    """Add disabled-by-default policy and bounded coordinator state."""
    with op.batch_alter_table("server_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_archive_mode",
                sa.String(length=32),
                nullable=False,
                server_default="disabled",
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_retention_days",
                sa.BigInteger(),
                nullable=False,
                server_default="180",
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_cursor_completed_at",
                sa.DateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_cursor_root_run_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_coordinator_owner",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_coordinator_token",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "execution_archive_coordinator_expires_at",
                sa.DateTime(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("execution_archive_last_pass", sa.Text(), nullable=True)
        )

    op.create_index(
        "ix_pipeline_run_archive_candidates",
        "pipeline_run",
        [
            "execution_archive_id",
            "end_time",
            "id",
        ],
        unique=False,
    )


def downgrade() -> None:
    """Remove product coordination only when no work depends on it.

    Raises:
        RuntimeError: If archive authority or an object purge is outstanding.
    """
    archive = sa.table(
        "execution_archive",
        sa.column("state", sa.String(length=32)),
        sa.column("compacted_at", sa.DateTime()),
        sa.column("restored_at", sa.DateTime()),
        sa.column("purge_pending_at", sa.DateTime()),
    )
    unsafe = (
        op.get_bind()
        .execute(
            sa.select(sa.func.count())
            .select_from(archive)
            .where(
                sa.or_(
                    archive.c.state.in_(_AUTHORITATIVE_STATES),
                    sa.and_(
                        archive.c.state == "corrupt",
                        archive.c.compacted_at.is_not(None),
                        archive.c.restored_at.is_(None),
                    ),
                    archive.c.purge_pending_at.is_not(None),
                )
            )
        )
        .scalar_one()
    )
    if unsafe:
        raise RuntimeError(
            "Restore all authoritative execution archives and drain queued "
            "object purges before downgrading archive coordination."
        )
    op.drop_index(
        "ix_pipeline_run_archive_candidates",
        table_name="pipeline_run",
    )
    with op.batch_alter_table("server_settings") as batch_op:
        batch_op.drop_column("execution_archive_last_pass")
        batch_op.drop_column("execution_archive_coordinator_expires_at")
        batch_op.drop_column("execution_archive_coordinator_token")
        batch_op.drop_column("execution_archive_coordinator_owner")
        batch_op.drop_column("execution_archive_cursor_root_run_id")
        batch_op.drop_column("execution_archive_cursor_completed_at")
        batch_op.drop_column("execution_archive_retention_days")
        batch_op.drop_column("execution_archive_mode")
