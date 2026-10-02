"""Index run cascade foreign keys [4f2b8c1d9a37].

Revision ID: 4f2b8c1d9a37
Revises: d91e2f4a6b3c
Create Date: 2026-08-05 12:00:00.000000

"""

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "4f2b8c1d9a37"
down_revision = "d91e2f4a6b3c"
branch_labels = None
depends_on = None

# Foreign key child columns in the cascade closure of a pipeline run deletion
# that no index leads on. SQLite does not create indexes for foreign keys, and
# runs `SELECT rowid FROM <child> WHERE <child key> = ?` for every parent row it
# deletes, so each of these was a full table scan of the child table per deleted
# row: the cost of deleting a run grew with the size of the whole store rather
# than with the size of the run. Restricted to the tables that grow with
# pipeline runs -- indexing the ones that do not would only add write cost.
#
# These are created on MySQL too, where they are not extra indexes: InnoDB
# auto-creates an index for every foreign key, and drops that implicit index
# once an equivalent user index can serve the constraint. Measured over these
# columns on MySQL 8.4.11, the index count per affected table and the foreign
# key count were identical before and after, so the net effect there is a
# rename. Do not drop the implicit `fk_*` indexes on the assumption that these
# duplicate them, and do not restrict this to SQLite on the assumption that
# they do.
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

# `ix_pipeline_run_root_run_id` is also created by `c2f8d07a91b4`, so the two
# paths into the schema disagree about it: a database old enough to have run
# that migration has the index, while one created from the schema afterwards
# does not, because `PipelineRunSchema` did not declare it until this revision.
# The upgrade therefore has to create it for the second group without failing
# for the first, which is why every index here is created only if it is absent.
# The downgrade leaves this one alone -- `c2f8d07a91b4` owns it and drops it.
EXTERNALLY_OWNED_INDEXES = {"ix_pipeline_run_root_run_id"}


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    inspector = inspect(op.get_bind())
    existing_indexes = {
        table_name: {
            index["name"] for index in inspector.get_indexes(table_name)
        }
        for table_name, _ in INDEXED_COLUMNS
    }

    for table_name, column_name in INDEXED_COLUMNS:
        index_name = f"ix_{table_name}_{column_name}"
        if index_name in existing_indexes[table_name]:
            continue

        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.create_index(
                index_name,
                [column_name],
                unique=False,
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table_name, column_name in reversed(INDEXED_COLUMNS):
        index_name = f"ix_{table_name}_{column_name}"
        if index_name in EXTERNALLY_OWNED_INDEXES:
            continue

        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(index_name)
