"""Add step input values and snapshot execution overrides [9bd3aeb2c17e].

Revision ID: 9bd3aeb2c17e
Revises: b6f2a8d9c3e1
Create Date: 2026-07-15 00:00:00.000000

"""

import json
from typing import Any, Dict

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "9bd3aeb2c17e"
down_revision = "b6f2a8d9c3e1"
branch_labels = None
depends_on = None


def _convert_input_overrides(
    overrides: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """Convert legacy artifact version input overrides to input sources.

    Args:
        overrides: The legacy input overrides, mapping input names to
            artifact version IDs.

    Returns:
        The converted input source overrides.
    """
    return {
        key: {
            input_name: {
                "type": "artifact_version",
                "id": artifact_version_id,
            }
            for input_name, artifact_version_id in value.items()
        }
        for key, value in overrides.items()
    }


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "input_values",
                sa.String(length=16777215).with_variant(
                    mysql.MEDIUMTEXT, "mysql"
                ),
                nullable=True,
            )
        )

    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "execution_overrides",
                sa.String(length=16777215).with_variant(
                    mysql.MEDIUMTEXT, "mysql"
                ),
                nullable=True,
            )
        )

    # Move legacy execution overrides stored in the pipeline configuration
    # to the new column. The pipeline configurations are fetched in chunks
    # to limit memory usage for large tables.
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=("pipeline_snapshot",))
    snapshot_table = sa.Table("pipeline_snapshot", meta)

    chunk_size = 500
    snapshot_ids = (
        connection.execute(sa.select(snapshot_table.c.id)).scalars().all()
    )

    for chunk_start in range(0, len(snapshot_ids), chunk_size):
        id_chunk = snapshot_ids[chunk_start : chunk_start + chunk_size]
        snapshot_updates = []

        for snapshot_id, pipeline_configuration_json in connection.execute(
            sa.select(
                snapshot_table.c.id,
                snapshot_table.c.pipeline_configuration,
            ).where(snapshot_table.c.id.in_(id_chunk))
        ):
            pipeline_configuration = json.loads(pipeline_configuration_json)

            steps_to_skip = pipeline_configuration.get("steps_to_skip") or []
            skip_successful_steps = pipeline_configuration.get(
                "skip_successful_steps", False
            )
            input_overrides = (
                pipeline_configuration.get("step_input_overrides") or {}
            )
            default_input_overrides = (
                pipeline_configuration.get("step_default_input_overrides")
                or {}
            )

            if not (
                steps_to_skip
                or skip_successful_steps
                or input_overrides
                or default_input_overrides
            ):
                continue

            execution_overrides = {
                "steps_to_skip": steps_to_skip,
                "skip_successful_steps": skip_successful_steps,
                "input_overrides": _convert_input_overrides(input_overrides),
                "default_input_overrides": _convert_input_overrides(
                    default_input_overrides
                ),
            }

            for key in (
                "steps_to_skip",
                "skip_successful_steps",
                "step_input_overrides",
                "step_default_input_overrides",
            ):
                pipeline_configuration.pop(key, None)

            snapshot_updates.append(
                {
                    "id_": snapshot_id,
                    "pipeline_configuration": json.dumps(
                        pipeline_configuration
                    ),
                    "execution_overrides": json.dumps(execution_overrides),
                }
            )

        if snapshot_updates:
            connection.execute(
                sa.update(snapshot_table).where(
                    snapshot_table.c.id == sa.bindparam("id_")
                ),
                snapshot_updates,
            )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.drop_column("execution_overrides")

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("input_values")
