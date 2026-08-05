"""Index run cascade foreign keys [4f2b8c1d9a37].

Revision ID: 4f2b8c1d9a37
Revises: 0.96.2
Create Date: 2026-08-05 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4f2b8c1d9a37"
down_revision = "0.96.2"
branch_labels = None
depends_on = None

# Foreign key child columns in the cascade closure of a pipeline run deletion
# that no index leads on. SQLite does not create indexes for foreign keys, and
# runs `SELECT rowid FROM <child> WHERE <child key> = ?` for every parent row it
# deletes, so each of these was a full table scan of the child table per deleted
# row: the cost of deleting a run grew with the size of the whole store rather
# than with the size of the run. Restricted to the tables that grow with
# pipeline runs -- indexing the ones that do not would only add write cost.
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
    ("pipeline_run", "original_run_id"),
]

# `ix_pipeline_run_root_run_id` is deliberately absent: `c2f8d07a91b4` already
# creates it, so an upgraded database has it and creating it again fails. It was
# missing from `PipelineRunSchema.__table_args__` though, which left databases
# created from the schema without it -- that is fixed in the schema, so both
# paths now end up with the same index.


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    for table_name, column_name in INDEXED_COLUMNS:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.create_index(
                f"ix_{table_name}_{column_name}",
                [column_name],
                unique=False,
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table_name, column_name in reversed(INDEXED_COLUMNS):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_{column_name}")
