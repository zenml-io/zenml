"""Add artifact version reference indexes [2c713d3c1584].

Revision ID: 2c713d3c1584
Revises: 8d638fcb4bd5
Create Date: 2026-11-06 00:21:13.546785

"""

from alembic import op

from zenml.zen_stores.migrations.utils import (
    create_index_if_missing,
    drop_index_if_exists,
)

# revision identifiers, used by Alembic.
revision = "2c713d3c1584"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None

# The liveness check behind `only_unused` and pruning probes each of these
# columns once per artifact version. MySQL indexes foreign keys on its own,
# SQLite does not.
REFERENCING_COLUMNS = [
    ("step_run_input_artifact", "artifact_id"),
    ("step_run_output_artifact", "artifact_id"),
    ("pipeline_run_output", "artifact_id"),
    ("hook_invocation_output_artifact", "artifact_version_id"),
    ("model_versions_artifacts", "artifact_version_id"),
]


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Migration c2f8d07a91b4 already created the pipeline_run_output index
    # on migrated databases, but the schema never declared it.
    for table, column in REFERENCING_COLUMNS:
        create_index_if_missing(table, f"ix_{table}_{column}", [column])


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    # MySQL replaced its implicit foreign key indexes with these on upgrade
    # and refuses to drop them (error 1553), so they stay.
    if op.get_bind().dialect.name == "mysql":
        return
    for table, column in REFERENCING_COLUMNS:
        if table != "pipeline_run_output":
            drop_index_if_exists(table, f"ix_{table}_{column}")
