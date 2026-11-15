"""Index run cascade foreign keys [4f2b8c1d9a37].

Revision ID: 4f2b8c1d9a37
Revises: 8d638fcb4bd5
Create Date: 2026-08-05 12:00:00.000000

"""

from typing import Set

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "4f2b8c1d9a37"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None

# Foreign key child columns in the cascade closure of a pipeline run deletion
# that SQLite had no index on. SQLite does not create indexes for foreign keys,
# and runs `SELECT rowid FROM <child> WHERE <child key> = ?` for every parent
# row it deletes, so each of these was a full table scan of the child table per
# deleted row: the cost of deleting a run grew with the size of the whole store rather
# than with the size of the run. Restricted to the tables that grow with
# pipeline runs -- indexing the ones that do not would only add write cost.
#
# A column is skipped if any index already leads on it, whatever its name,
# because that index serves the cascade just as well. Three cases depend on it:
# - `ix_pipeline_run_root_run_id` is also created by `c2f8d07a91b4`, so a
#   database old enough to have run that migration has it, while one created
#   from the schema afterwards does not.
# - On MySQL, InnoDB auto-creates an index for every foreign key, so an upgraded
#   MySQL database already has all of these and the upgrade adds nothing.
# - A MySQL database restored with `mysqldump` has those implicit indexes as
#   explicit keys, which InnoDB keeps next to any new index on the same column.
#   Matching on the name only would double them up there.
INDEXED_COLUMNS = [
    ("step_run", "pipeline_run_id"),
    ("step_run", "original_step_run_id"),
    ("step_run_input_artifact", "step_id"),
    ("step_run_parents", "child_id"),
    ("logs", "pipeline_run_id"),
    ("logs", "step_run_id"),
    ("hook_invocation", "pipeline_run_id"),
    ("hook_invocation", "step_run_id"),
    ("run_metadata", "publisher_step_id"),
    ("run_metadata_resource", "run_metadata_id"),
    ("model_versions_runs", "pipeline_run_id"),
    ("service", "pipeline_run_id"),
    ("trigger_execution", "pipeline_run_id"),
    ("pipeline_run", "root_run_id"),
    ("pipeline_run", "original_run_id"),
]


def _indexed_columns(table_name: str) -> Set[str]:
    """Get the columns of a table that an index leads on.

    Args:
        table_name: The table to inspect.

    Returns:
        The leading column of every index on the table.
    """
    inspector = inspect(op.get_bind())
    return {
        index["column_names"][0]
        for index in inspector.get_indexes(table_name)
        if index["column_names"] and index["column_names"][0]
    }


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    indexed_columns = {
        table_name: _indexed_columns(table_name)
        for table_name, _ in INDEXED_COLUMNS
    }

    for table_name, column_name in INDEXED_COLUMNS:
        if column_name in indexed_columns[table_name]:
            continue

        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.create_index(
                f"ix_{table_name}_{column_name}",
                [column_name],
                unique=False,
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Left empty: the upgrade skips columns that were already indexed, so the
    downgrade cannot tell which indexes it created, and on MySQL an index that
    serves a foreign key cannot be dropped anyway.
    """
    pass
