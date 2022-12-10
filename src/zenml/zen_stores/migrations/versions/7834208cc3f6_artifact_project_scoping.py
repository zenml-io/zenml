"""Artifact Project Scoping [7834208cc3f6].

Revision ID: 7834208cc3f6
Revises: 10a907dad202
Create Date: 2022-12-06 10:08:28.031325

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import select

# revision identifiers, used by Alembic.
revision = "7834208cc3f6"
down_revision = "10a907dad202"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # ------------------------------------
    # Add new columns, for now as nullable
    # ------------------------------------

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )

    # ------------
    # Migrate data
    # ------------

    conn = op.get_bind()
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(
        only=(
            "pipeline_run",
            "step_run",
            "artifact",
            "step_run_output_artifact",
            "workspace",
        )
    )
    pipeline_runs = sa.Table("pipeline_run", meta)
    step_runs = sa.Table("step_run", meta)
    artifacts = sa.Table("artifact", meta)
    step_run_output_artifacts = sa.Table("step_run_output_artifact", meta)
    workspace = sa.Table("workspace", meta)

    # Use the first workspace as the default workspace in case an artifact or
    # step run has no associated pipeline run or producer step run.
    default_workspace = conn.execute(select([workspace])).first()

    # For each step run, set user and project according to its pipeline run
    for step_run in conn.execute(select([step_runs])).all():
        pipeline_run = conn.execute(
            select([pipeline_runs]).where(
                pipeline_runs.c.id == step_run.pipeline_run_id
            )
        ).first()
        if pipeline_run is not None:
            project_id = pipeline_run.project_id
            user_id = pipeline_run.user_id
        else:
            assert default_workspace is not None
            project_id = default_workspace.id
            user_id = None
        conn.execute(
            step_runs.update()
            .where(step_runs.c.id == step_run.id)
            .values(user_id=user_id, project_id=project_id)
        )

    # For each artifact, set user and project according to its producer step run
    for artifact in conn.execute(select([artifacts])).all():
        producer_step_run = conn.execute(
            select([step_runs])
            .where(step_runs.c.status == "completed")
            .where(step_runs.c.id == step_run_output_artifacts.c.step_id)
            .where(step_run_output_artifacts.c.artifact_id == artifact.id)
        ).first()
        if producer_step_run is not None:
            project_id = producer_step_run.project_id
            user_id = producer_step_run.user_id
        else:
            assert default_workspace is not None
            project_id = default_workspace.id
            user_id = None
        conn.execute(
            artifacts.update()
            .where(artifacts.c.id == artifact.id)
            .values(user_id=user_id, project_id=project_id)
        )

    # ------------------------------------
    # Change nullable and add foreign keys
    # ------------------------------------

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.GUID(),
        )
        batch_op.create_foreign_key(
            "fk_artifact_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_artifact_project_id_workspace",
            "workspace",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            nullable=False,
            existing_type=sqlmodel.sql.sqltypes.GUID(),
        )
        batch_op.create_foreign_key(
            "fk_step_run_project_id_workspace",
            "workspace",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_step_run_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade is not supported for this migration.
    """
    raise NotImplementedError("Downgrade not supported.")
