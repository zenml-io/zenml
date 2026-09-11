"""Enforce step configuration uniqueness [b02cab3094ca].

Revision ID: b02cab3094ca
Revises: 0.96.3
Create Date: 2026-08-28 12:52:43.490193

A step configuration belongs to either a pipeline snapshot or a dynamic step
run, so one of the two owner columns is always NULL. Since ``af27025fe19c``
(0.92.0) the only unique constraint spanned both owner columns, and because SQL
treats NULL as distinct it never rejected a duplicate name. This revision
replaces it with one constraint per owner: a snapshot holds one configuration
per step name, a step run holds exactly one configuration. The two non-unique
indexes on the owner columns are dropped because the new unique indexes cover
the same lookups.

The upgrade refuses to run while rows violate the new constraints. The store
never writes such rows, so they can only come from manual edits and there is
no safe way to pick which one to keep.
"""

from typing import Any

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


def _assert_no_duplicates(*columns: sa.ColumnClause[Any]) -> None:
    """Fail if several rows share the given owner column values.

    Args:
        *columns: The owner column followed by any further columns that make
            up the new unique key.

    Raises:
        RuntimeError: If duplicate rows exist.
    """
    owner = columns[0]
    duplicates = (
        op.get_bind()
        .execute(
            sa.select(*columns)
            .where(owner.is_not(None))
            .group_by(*columns)
            .having(sa.func.count() > 1)
            .limit(10)
        )
        .fetchall()
    )
    if duplicates:
        key = ", ".join(f"`{column.name}`" for column in columns)
        raise RuntimeError(
            f"Unable to migrate database because the `{TABLE_NAME}` table "
            f"contains several rows with the same {key}, for example "
            f"{[tuple(row) for row in duplicates]}. Remove the duplicate rows "
            "before upgrading. Note that MySQL compares names according to "
            "the column collation, which by default ignores case, so rows "
            "whose names differ only in case are reported as duplicates too."
        )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    table = sa.table(
        TABLE_NAME,
        sa.column("snapshot_id"),
        sa.column("step_run_id"),
        sa.column("name"),
    )
    _assert_no_duplicates(table.c.snapshot_id, table.c.name)
    _assert_no_duplicates(table.c.step_run_id)

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        # MySQL requires an index starting with the foreign key column for
        # each foreign key. The replacement constraints provide those indexes,
        # so they must exist before the old constraint and indexes are dropped.
        batch_op.create_unique_constraint(
            SNAPSHOT_UNIQUE_CONSTRAINT, ["snapshot_id", "name"]
        )
        batch_op.create_unique_constraint(
            STEP_RUN_UNIQUE_CONSTRAINT, ["step_run_id"]
        )
        batch_op.drop_constraint(OLD_UNIQUE_CONSTRAINT, type_="unique")
        batch_op.drop_index(SNAPSHOT_INDEX)
        batch_op.drop_index(STEP_RUN_INDEX)


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.create_unique_constraint(
            OLD_UNIQUE_CONSTRAINT, ["snapshot_id", "step_run_id", "name"]
        )
        batch_op.create_index(
            SNAPSHOT_INDEX, ["snapshot_id", "name"], unique=False
        )
        batch_op.create_index(STEP_RUN_INDEX, ["step_run_id"], unique=False)
        batch_op.drop_constraint(SNAPSHOT_UNIQUE_CONSTRAINT, type_="unique")
        batch_op.drop_constraint(STEP_RUN_UNIQUE_CONSTRAINT, type_="unique")
