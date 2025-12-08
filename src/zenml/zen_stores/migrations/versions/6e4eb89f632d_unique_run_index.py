"""Unique run index [6e4eb89f632d].

Revision ID: 6e4eb89f632d
Revises: 5c0a1c787128
Create Date: 2025-12-03 17:27:32.828004

"""

from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e4eb89f632d"
down_revision = "5c0a1c787128"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("run_count", sa.Integer(), nullable=True)
        )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("index", sa.Integer(), nullable=True))

    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=("pipeline_run", "pipeline"))
    run_table = sa.Table("pipeline_run", meta)
    pipeline_table = sa.Table("pipeline", meta)

    # Some very old runs (version <0.34.0) might not have a pipeline ID in the
    # rare case where the associated pipeline was deleted after the migration
    # with revision `8ad841ad9bfe`.
    connection.execute(
        sa.update(run_table)
        .where(run_table.c.pipeline_id.is_(None))
        .values(index=0)
    )

    result = connection.execute(
        sa.select(
            run_table.c.id,
            run_table.c.pipeline_id,
        )
        .where(run_table.c.pipeline_id.is_not(None))
        .order_by(run_table.c.pipeline_id, run_table.c.created, run_table.c.id)
    ).fetchall()

    current_pipeline_id = None
    index_within_pipeline = 0
    run_updates: list[dict[str, Any]] = []
    run_counts: dict[str, int] = {}
    for row in result:
        pipeline_id = row.pipeline_id
        if pipeline_id != current_pipeline_id:
            current_pipeline_id = pipeline_id
            index_within_pipeline = 1
        else:
            index_within_pipeline += 1
        run_updates.append({"id_": row.id, "index": index_within_pipeline})
        run_counts[pipeline_id] = index_within_pipeline

    update_batch_size = 10000
    if run_updates:
        update_statement = (
            sa.update(run_table)
            .where(run_table.c.id == sa.bindparam("id_"))
            .values(index=sa.bindparam("index"))
        )

        for start in range(0, len(run_updates), update_batch_size):
            batch = run_updates[start : start + update_batch_size]
            if batch:
                connection.execute(update_statement, batch)

    if run_counts:
        pipeline_updates = [
            {"id_": pipeline_id, "run_count": run_count}
            for pipeline_id, run_count in run_counts.items()
        ]
        update_statement = (
            sa.update(pipeline_table)
            .where(pipeline_table.c.id == sa.bindparam("id_"))
            .values(run_count=sa.bindparam("run_count"))
        )
        for start in range(0, len(pipeline_updates), update_batch_size):
            batch = pipeline_updates[start : start + update_batch_size]
            if batch:
                connection.execute(update_statement, batch)

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.alter_column(
            "index", existing_type=sa.Integer(), nullable=False
        )

    with op.batch_alter_table("pipeline", schema=None) as batch_op:
        batch_op.alter_column(
            "run_count", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("number")

    with op.batch_alter_table("pipeline", schema=None) as batch_op:
        batch_op.drop_column("run_count")
