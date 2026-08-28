"""Add artifact version reference indexes [e50a6a75e6b4].

Revision ID: e50a6a75e6b4
Revises: 0.96.3
Create Date: 2026-08-28 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e50a6a75e6b4"
down_revision = "0.96.3"
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


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    for table, column in REFERENCING_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_index(
                f"ix_{table}_{column}", [column], unique=False
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    for table, column in REFERENCING_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table}_{column}")
