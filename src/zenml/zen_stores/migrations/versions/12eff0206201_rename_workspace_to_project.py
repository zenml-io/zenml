"""rename workspace to project [12eff0206201].

Revision ID: 12eff0206201
Revises: cbc6acd71f92
Create Date: 2025-03-12 22:34:29.670973

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "12eff0206201"
down_revision = "cbc6acd71f92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Create the new project table first
    op.create_table(
        "project",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="unique_project_name"),
    )

    # Copy data from workspace to project
    op.execute(
        """
        INSERT INTO `project` (id, created, updated, name, display_name, description)
        SELECT id, created, updated, name, display_name, description
        FROM `workspace`
        """
    )

    # For each table that needs migration, we'll:
    # 1. Add new column as nullable
    # 2. Copy data
    # 3. Make column non-nullable and add constraints

    # Example for one table (repeat pattern for others)
    with op.batch_alter_table("action", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `action` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_action_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_action_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_action_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_action_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `artifact` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_artifact_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_artifact_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_artifact_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_artifact_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `artifact_version` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_artifact_version_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_artifact_version_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("code_reference", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `code_reference` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("code_reference", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_code_reference_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_code_reference_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `code_repository` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_code_repository_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_code_repository_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_code_repository_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_code_repository_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("event_source", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `event_source` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("event_source", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_event_source_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_event_source_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_event_source_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_event_source_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("model", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `model` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("model", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_model_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_model_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_model_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_model_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("model_version", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `model_version` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("model_version", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_model_version_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_model_version_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("pipeline", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `pipeline` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("pipeline", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_pipeline_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_pipeline_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_pipeline_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_pipeline_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # pipeline_build table
    with op.batch_alter_table("pipeline_build", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `pipeline_build` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("pipeline_build", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_pipeline_build_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_pipeline_build_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # pipeline_deployment table
    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `pipeline_deployment` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_pipeline_deployment_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # pipeline_run table
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `pipeline_run` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_run_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_run_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_pipeline_run_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_pipeline_run_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # run_metadata table
    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `run_metadata` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_run_metadata_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_run_metadata_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # run_template table
    with op.batch_alter_table("run_template", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `run_template` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("run_template", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_template_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_template_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_run_template_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_run_template_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # schedule table
    with op.batch_alter_table("schedule", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `schedule` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_schedule_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_schedule_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_schedule_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_schedule_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # service table
    with op.batch_alter_table("service", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `service` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_service_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_service_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # step_run table
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `step_run` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "fk_step_run_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_step_run_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    # trigger table
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        # Phase 1: Add new column as nullable
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )

    # Phase 2: Copy data
    op.execute(
        """
        UPDATE `trigger` 
        SET project_id = workspace_id
        """
    )

    # Phase 3: Add constraints and drop old column
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "unique_trigger_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint(
            "unique_trigger_name_in_project", ["name", "project_id"]
        )
        batch_op.drop_constraint(
            "fk_trigger_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_trigger_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_user_default_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("default_workspace_id")

    op.drop_table("workspace")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not implemented
    """
    raise NotImplementedError("Downgrade is not implemented")
