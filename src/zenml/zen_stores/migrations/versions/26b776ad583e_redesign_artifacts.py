"""Redesign Artifacts [26b776ad583e].

Revision ID: 26b776ad583e
Revises: 0.23.0
Create Date: 2022-11-17 08:00:24.936750

"""

from typing import Any, Dict

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import select
from sqlalchemy.sql.expression import false, true

# revision identifiers, used by Alembic.
revision = "26b776ad583e"
down_revision = "0.23.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ----------------
    # Create new table
    # ----------------
    op.create_table(
        "step_run_output_artifact",
        sa.Column("step_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("artifact_id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_step_run_output_artifact_artifact_id_artifacts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["step_run.id"],
            name="fk_step_run_output_artifact_step_id_step_run",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("step_id", "artifact_id"),
    )

    # ------------
    # Migrate data
    # ------------
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(
        bind=op.get_bind(),
        only=(
            "artifacts",
            "step_run_output_artifact",
            "step_run_input_artifact",
        ),
    )
    artifacts = sa.Table("artifacts", meta)
    step_run_output_artifact = sa.Table("step_run_output_artifact", meta)
    step_run_input_artifact = sa.Table("step_run_input_artifact", meta)

    # Get all artifacts that were actually produced and not cached.
    produced_artifacts = conn.execute(
        select(
            artifacts.c.id,
            artifacts.c.name,
            artifacts.c.parent_step_id,
            artifacts.c.producer_step_id,
        ).where(artifacts.c.is_cached == false())
    ).fetchall()

    # Get all cached artifacts, these are all copies of some produced artifacts.
    cached_artifacts = conn.execute(
        select(
            artifacts.c.id,
            artifacts.c.name,
            artifacts.c.parent_step_id,
            artifacts.c.producer_step_id,
        ).where(artifacts.c.is_cached == true())
    ).fetchall()

    def _find_produced_artifact(cached_artifact: Any) -> Any:
        """For a given cached artifact, find the original produced artifact.

        Args:
            cached_artifact: The cached artifact to find the original for.

        Returns:
            The original produced artifact.

        Raises:
            ValueError: If the original produced artifact could not be found.
        """
        for produced_artifact in produced_artifacts:
            if (
                cached_artifact.name == produced_artifact.name
                and cached_artifact.producer_step_id
                == produced_artifact.producer_step_id
            ):
                return produced_artifact
        raise ValueError(
            "Could not find produced artifact for cached artifact"
        )

    # For each cached artifact, find the ID of the original produced artifact
    # and link all input artifact entries to the produced artifact.
    cached_to_produced_mapping: Dict[str, str] = {}
    for cached_artifact in cached_artifacts:
        produced_artifact = _find_produced_artifact(cached_artifact)
        cached_to_produced_mapping[cached_artifact.id] = produced_artifact.id
        conn.execute(
            step_run_input_artifact.update()
            .where(step_run_input_artifact.c.artifact_id == cached_artifact.id)
            .values({"artifact_id": produced_artifact.id})
        )

    # Delete all cached artifacts from the artifacts table
    conn.execute(artifacts.delete().where(artifacts.c.is_cached == true()))

    # Insert all produced and cached artifacts into the output artifact table
    produced_output_artifacts = [
        {
            "step_id": produced_artifact.parent_step_id,
            "artifact_id": produced_artifact.id,
            "name": produced_artifact.name,
        }
        for produced_artifact in produced_artifacts
    ]
    cached_output_artifacts = [
        {
            "step_id": cached_artifact.parent_step_id,
            "artifact_id": cached_to_produced_mapping[cached_artifact.id],
            "name": cached_artifact.name,
        }
        for cached_artifact in cached_artifacts
    ]
    output_artifacts = produced_output_artifacts + cached_output_artifacts

    if output_artifacts:
        conn.execute(
            step_run_output_artifact.insert().values(output_artifacts)
        )

    # --------------
    # Adjust columns
    # --------------
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        # Add artifact store link column
        batch_op.add_column(
            sa.Column(
                "artifact_store_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_artifacts_artifact_store_id_stack_component",
            "stack_component",
            ["artifact_store_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Drop old parent and producer step columns
        batch_op.drop_constraint(
            "fk_artifacts_producer_step_id_step_run", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_artifacts_parent_step_id_step_run", type_="foreignkey"
        )
        batch_op.drop_column("parent_step_id")
        batch_op.drop_column("producer_step_id")
        batch_op.drop_column("is_cached")
        batch_op.drop_column("mlmd_parent_step_id")
        batch_op.drop_column("mlmd_producer_step_id")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not supported for this migration.
    """
    raise NotImplementedError("Downgrade not supported.")
