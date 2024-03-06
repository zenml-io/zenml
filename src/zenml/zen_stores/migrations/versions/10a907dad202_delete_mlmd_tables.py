"""Delete MLMD [10a907dad202].

Revision ID: 10a907dad202
Revises: 6a28c4fd0ef2
Create Date: 2022-11-24 19:07:24.698583

"""

from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "10a907dad202"
down_revision = "6a28c4fd0ef2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Bye bye MLMD :wave: :wave: :wave:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    for table in (
        "Artifact",
        "ArtifactProperty",
        "Association",
        "Attribution",
        "Context",
        "ContextProperty",
        "Event",
        "EventPath",
        "Execution",
        "ExecutionProperty",
        "ParentContext",
        "ParentType",
        "Type",
        "TypeProperty",
        "MLMDEnv",
    ):
        if table in tables:
            op.drop_table(table)

    # Bye bye mlmd_id :wave: :wave: :wave:
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_column("mlmd_id")

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("mlmd_id")

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("mlmd_id")

    # Rename table 'artifacts' to 'artifact' now that MLMD no longer uses it.
    with op.batch_alter_table("step_run_input_artifact") as batch_op:
        batch_op.drop_constraint(
            "fk_step_run_input_artifact_artifact_id_artifacts",
            type_="foreignkey",
        )

    with op.batch_alter_table("step_run_output_artifact") as batch_op:
        batch_op.drop_constraint(
            "fk_step_run_output_artifact_artifact_id_artifacts",
            type_="foreignkey",
        )

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint(
            "fk_artifacts_artifact_store_id_stack_component",
            type_="foreignkey",
        )

    op.rename_table("artifacts", "artifact")

    with op.batch_alter_table("step_run_input_artifact") as batch_op:
        batch_op.create_foreign_key(
            "fk_step_run_input_artifact_artifact_id_artifact",
            "artifact",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("step_run_output_artifact") as batch_op:
        batch_op.create_foreign_key(
            "fk_step_run_output_artifact_artifact_id_artifact",
            "artifact",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("artifact") as batch_op:
        batch_op.create_foreign_key(
            "fk_artifact_artifact_store_id_stack_component",
            "stack_component",
            ["artifact_store_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not supported for this migration.
    """
    raise NotImplementedError("Downgrade not supported.")
