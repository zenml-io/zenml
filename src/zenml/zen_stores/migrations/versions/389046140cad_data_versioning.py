"""Data Versioning [389046140cad].

Revision ID: 389046140cad
Revises: 86fa52918b54
Create Date: 2023-10-09 14:12:01.280877

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "389046140cad"
down_revision = "86fa52918b54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Artifacts Table
    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("has_custom_name", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "version", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("version_number", sa.Integer(), nullable=True)
        )

    op.execute("UPDATE artifact SET has_custom_name = FALSE")
    op.execute("UPDATE artifact SET version = 'UNVERSIONED'")
    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.alter_column(
            "has_custom_name",
            nullable=False,
            existing_type=sa.Boolean(),
        )
        batch_op.alter_column(
            "version",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
        )

    # Step Run Input/Output Artifacts Tables
    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "type", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "type", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
    op.execute("UPDATE step_run_input_artifact SET type = 'default'")
    op.execute("UPDATE step_run_output_artifact SET type = 'default'")
    with op.batch_alter_table(
        "step_run_input_artifact", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "type",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
        )
    with op.batch_alter_table(
        "step_run_output_artifact", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "type",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
        )

    # Model Version Artifacts and Runs Tables
    # Drop all entries with null IDs
    op.execute(
        "DELETE FROM model_versions_artifacts WHERE artifact_id IS NULL"
    )
    op.execute("DELETE FROM model_versions_runs WHERE pipeline_run_id IS NULL")
    # Make IDs non-nullable and drop unused columns
    with op.batch_alter_table(
        "model_versions_artifacts", schema=None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_model_versions_artifacts_artifact_id_artifact",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "artifact_id", existing_type=sa.CHAR(length=32), nullable=False
        )
        batch_op.create_foreign_key(
            "fk_model_versions_artifacts_artifact_id_artifact",
            "artifact",
            ["artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("step_name")
        batch_op.drop_column("version")
        batch_op.drop_column("pipeline_name")
        batch_op.drop_column("name")
    with op.batch_alter_table("model_versions_runs", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_model_versions_runs_run_id_pipeline_run",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "pipeline_run_id", existing_type=sa.CHAR(length=32), nullable=False
        )
        batch_op.create_foreign_key(
            "fk_model_versions_runs_pipeline_run_id_pipeline_run",
            "pipeline_run",
            ["pipeline_run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("name")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not implemented for this migration
            because the migration drops non-nullable columns.
    """
    raise NotImplementedError(
        "Downgrade is not implemented for this migration."
    )
