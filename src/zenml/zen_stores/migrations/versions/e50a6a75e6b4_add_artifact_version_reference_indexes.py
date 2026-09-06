"""Add artifact version reference indexes [e50a6a75e6b4].

Revision ID: e50a6a75e6b4
Revises: 0.96.4
Create Date: 2026-08-28 12:00:00.000000

"""

from zenml.zen_stores.migrations.utils import (
    create_index_if_missing,
    drop_index_if_exists,
)

# revision identifiers, used by Alembic.
revision = "e50a6a75e6b4"
down_revision = "0.96.4"
branch_labels = None
depends_on = None

# Every table that references an artifact version, with the referencing
# column. MySQL indexes foreign keys on its own, SQLite does not, and the
# liveness check behind `only_unused` and pruning probes each of these
# columns once per artifact version.
REFERENCING_COLUMNS = [
    ("step_run_input_artifact", "artifact_id"),
    ("step_run_output_artifact", "artifact_id"),
    ("pipeline_run_output", "artifact_id"),
    ("hook_invocation_output_artifact", "artifact_version_id"),
    ("model_versions_artifacts", "artifact_version_id"),
]


def _index_name(table: str, column: str) -> str:
    # Same naming as `schema_utils.get_index_name`, which the schemas use.
    return f"ix_{table}_{column}"


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Databases that went through migration c2f8d07a91b4 already have the
    # pipeline_run_output index; databases created from the schema metadata
    # do not, because the schema never declared it.
    for table, column in REFERENCING_COLUMNS:
        create_index_if_missing(table, _index_name(table, column), [column])


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table, column in REFERENCING_COLUMNS:
        # The pipeline_run_output index belongs to migration c2f8d07a91b4.
        if table != "pipeline_run_output":
            drop_index_if_exists(table, _index_name(table, column))
