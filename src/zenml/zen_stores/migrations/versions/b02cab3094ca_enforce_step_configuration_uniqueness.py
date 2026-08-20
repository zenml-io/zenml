"""Enforce step configuration uniqueness [b02cab3094ca].

Revision ID: b02cab3094ca
Revises: 0.96.3
Create Date: 2026-08-20 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b02cab3094ca"
down_revision = "0.96.3"
branch_labels = None
depends_on = None

TABLE_NAME = "step_configuration"
OLD_UNIQUE_CONSTRAINT = "unique_step_configuration_for_snapshot_or_step_run"
SNAPSHOT_UNIQUE_CONSTRAINT = "unique_step_configuration_for_snapshot"
STEP_RUN_UNIQUE_CONSTRAINT = "unique_step_configuration_for_step_run"
SNAPSHOT_INDEX = "ix_step_configuration_snapshot_id_name"
STEP_RUN_INDEX = "ix_step_configuration_step_run_id"


def _assert_no_duplicate_owner_names() -> None:
    """Abort before changing indexes if existing rows violate uniqueness."""
    table = sa.table(
        TABLE_NAME,
        sa.column("snapshot_id"),
        sa.column("step_run_id"),
        sa.column("name"),
    )
    connection = op.get_bind()

    for owner_column in (table.c.snapshot_id, table.c.step_run_id):
        duplicate = connection.execute(
            sa.select(owner_column, table.c.name)
            .where(owner_column.is_not(None))
            .group_by(owner_column, table.c.name)
            .having(sa.func.count() > 1)
            .limit(1)
        ).first()
        if duplicate is not None:
            raise RuntimeError(
                "Cannot enforce step configuration uniqueness: duplicate "
                f"({owner_column.name}, name) values exist."
            )


def upgrade() -> None:
    """Replace the ineffective nullable composite uniqueness constraint."""
    _assert_no_duplicate_owner_names()

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.create_unique_constraint(
            SNAPSHOT_UNIQUE_CONSTRAINT,
            ["snapshot_id", "name"],
        )
        batch_op.create_unique_constraint(
            STEP_RUN_UNIQUE_CONSTRAINT,
            ["step_run_id", "name"],
        )
        batch_op.drop_constraint(OLD_UNIQUE_CONSTRAINT, type_="unique")
        batch_op.drop_index(SNAPSHOT_INDEX)
        batch_op.drop_index(STEP_RUN_INDEX)


def downgrade() -> None:
    """Restore the previous constraints and supporting indexes."""
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.create_unique_constraint(
            OLD_UNIQUE_CONSTRAINT,
            ["snapshot_id", "step_run_id", "name"],
        )
        batch_op.create_index(
            SNAPSHOT_INDEX,
            ["snapshot_id", "name"],
            unique=False,
        )
        batch_op.create_index(
            STEP_RUN_INDEX,
            ["step_run_id"],
            unique=False,
        )
        batch_op.drop_constraint(
            SNAPSHOT_UNIQUE_CONSTRAINT,
            type_="unique",
        )
        batch_op.drop_constraint(
            STEP_RUN_UNIQUE_CONSTRAINT,
            type_="unique",
        )
