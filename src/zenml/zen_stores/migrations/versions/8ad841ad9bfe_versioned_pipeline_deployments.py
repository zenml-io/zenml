"""Versioned pipeline deployments [8ad841ad9bfe].

Revision ID: 8ad841ad9bfe
Revises: 0.84.0
Create Date: 2025-07-22 11:20:28.777003

"""

import uuid

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import mysql

from zenml.utils.time_utils import utc_now

# revision identifiers, used by Alembic.
revision = "8ad841ad9bfe"
down_revision = "0.84.0"
branch_labels = None
depends_on = None


def add_unlisted_pipeline_if_necessary() -> None:
    """Create pipelines for orphaned deployments without a pipeline reference."""
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=("pipeline_deployment", "pipeline"))

    pipeline_deployment_table = sa.Table("pipeline_deployment", meta)
    pipeline_table = sa.Table("pipeline", meta)

    projects_with_orphaned_deployments = connection.execute(
        sa.select(
            pipeline_deployment_table.c.project_id,
        )
        .where(pipeline_deployment_table.c.pipeline_id.is_(None))
        .group_by(pipeline_deployment_table.c.project_id)
    ).fetchall()

    if not projects_with_orphaned_deployments:
        return

    now = utc_now()

    for project_id in projects_with_orphaned_deployments:
        existing_pipeline = connection.execute(
            sa.select(pipeline_table.c.id)
            .where(pipeline_table.c.project_id == project_id)
            .where(pipeline_table.c.name == "unlisted")
        ).fetchone()

        if existing_pipeline:
            unlisted_pipeline_id = existing_pipeline[0]
        else:
            unlisted_pipeline_id = str(uuid.uuid4()).replace("-", "")
            connection.execute(
                sa.insert(pipeline_table).values(
                    id=unlisted_pipeline_id,
                    created=now,
                    updated=now,
                    name="unlisted",
                    description="Auto-created pipeline for deployments without pipeline reference",
                    project_id=project_id,
                    user_id=None,
                )
            )

        connection.execute(
            sa.update(pipeline_deployment_table)
            .where(pipeline_deployment_table.c.project_id == project_id)
            .where(pipeline_deployment_table.c.pipeline_id.is_(None))
            .values(pipeline_id=unlisted_pipeline_id)
        )


def migrate_run_templates() -> None:
    """Migrate run templates into the deployment table."""
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(
        bind=connection,
        only=("pipeline_deployment", "run_template", "tag_resource"),
    )

    pipeline_deployment_table = sa.Table("pipeline_deployment", meta)
    run_template_table = sa.Table("run_template", meta)
    tag_resource_table = sa.Table("tag_resource", meta)

    # Step 1: Update the `template_id` of deployments to the source deployment
    # id instead of the run template id.
    deployment_template_mapping = connection.execute(
        sa.select(
            pipeline_deployment_table.c.id,
            run_template_table.c.source_deployment_id,
        )
        .outerjoin(
            run_template_table,
            run_template_table.c.id == pipeline_deployment_table.c.template_id,
        )
        .where(pipeline_deployment_table.c.template_id.is_not(None))
    ).fetchall()

    deployment_updates = [
        {"id_": deployment_id, "source_deployment_id": source_deployment_id}
        for deployment_id, source_deployment_id in deployment_template_mapping
    ]
    if deployment_updates:
        connection.execute(
            sa.update(pipeline_deployment_table)
            .where(pipeline_deployment_table.c.id == sa.bindparam("id_"))
            .values(source_deployment_id=sa.bindparam("source_deployment_id")),
            deployment_updates,
        )

    # Step 2: Migrate tags from run templates to their source deployments
    tag_run_template_mapping = connection.execute(
        sa.select(
            tag_resource_table.c.tag_id,
            run_template_table.c.source_deployment_id,
        )
        .join(
            run_template_table,
            run_template_table.c.id == tag_resource_table.c.resource_id,
        )
        .where(tag_resource_table.c.resource_type == "run_template")
    ).fetchall()

    now = utc_now()

    tag_resource_insertions = [
        {
            "id": str(uuid.uuid4()).replace("-", ""),
            "created": now,
            "updated": now,
            "tag_id": tag_id,
            "resource_id": source_deployment_id,
            "resource_type": "pipeline_deployment",
        }
        for tag_id, source_deployment_id in tag_run_template_mapping
    ]
    if tag_resource_insertions:
        op.bulk_insert(tag_resource_table, tag_resource_insertions)

    # Step 3: Migrate non-hidden run templates to their source deployments
    # If there are multiple templates for the same source deployment, use the
    # name/description of the latest one.
    latest_templates_subquery = (
        sa.select(
            run_template_table.c.source_deployment_id,
            sa.func.max(run_template_table.c.created).label("created"),
        )
        .where(run_template_table.c.hidden.is_(False))
        .where(run_template_table.c.source_deployment_id.is_not(None))
        .group_by(run_template_table.c.source_deployment_id)
        .subquery()
    )
    latest_templates_query = sa.select(
        run_template_table.c.name,
        run_template_table.c.description,
        run_template_table.c.source_deployment_id,
    ).join(
        latest_templates_subquery,
        sa.and_(
            latest_templates_subquery.c.source_deployment_id
            == run_template_table.c.source_deployment_id,
            run_template_table.c.created
            == latest_templates_subquery.c.created,
        ),
    )

    deployment_updates = [
        {
            "id_": source_deployment_id,
            "version": template_name,
            "description": template_description,
        }
        for template_name, template_description, source_deployment_id in connection.execute(
            latest_templates_query
        ).fetchall()
    ]
    if deployment_updates:
        connection.execute(
            sa.update(pipeline_deployment_table)
            .where(pipeline_deployment_table.c.id == sa.bindparam("id_"))
            .values(
                version=sa.bindparam("version"),
                description=sa.bindparam("description"),
            ),
            deployment_updates,
        )


def fill_trigger_execution_project_id() -> None:
    """Fill the project_id of trigger_execution from the associated trigger."""
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=("trigger_execution", "trigger"))

    trigger_execution_table = sa.Table("trigger_execution", meta)
    trigger_table = sa.Table("trigger", meta)

    trigger_executions = connection.execute(
        sa.select(
            trigger_execution_table.c.id,
            trigger_table.c.project_id,
        ).join(
            trigger_table,
            trigger_table.c.id == trigger_execution_table.c.trigger_id,
        )
    ).fetchall()

    trigger_execution_updates = [
        {"id_": trigger_execution_id, "project_id": project_id}
        for trigger_execution_id, project_id in trigger_executions
    ]
    if trigger_execution_updates:
        connection.execute(
            sa.update(trigger_execution_table)
            .where(trigger_execution_table.c.id == sa.bindparam("id_"))
            .values(project_id=sa.bindparam("project_id")),
            trigger_execution_updates,
        )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    add_unlisted_pipeline_if_necessary()

    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "version", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "description",
                sa.String(length=16777215).with_variant(
                    mysql.MEDIUMTEXT(), "mysql"
                ),
                nullable=True,
            )
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_pipeline_id_pipeline", type_="foreignkey"
        )
        batch_op.alter_column(
            "pipeline_id", existing_type=sa.CHAR(length=32), nullable=False
        )
        batch_op.create_unique_constraint(
            "unique_version_for_pipeline_id", ["pipeline_id", "version"]
        )
        batch_op.create_foreign_key(
            "fk_pipeline_deployment_pipeline_id_pipeline",
            "pipeline",
            ["pipeline_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.add_column(
            sa.Column(
                "source_deployment_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )

    with op.batch_alter_table("trigger_execution", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "project_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "step_run_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.alter_column(
            "trigger_id", existing_type=sa.CHAR(length=32), nullable=True
        )
        batch_op.create_foreign_key(
            "fk_trigger_execution_step_run_id_step_run",
            "step_run",
            ["step_run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_trigger_execution_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_trigger_execution_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    fill_trigger_execution_project_id()

    with op.batch_alter_table("trigger_execution", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )

    migrate_run_templates()


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade not implemented.
    """
    raise NotImplementedError("Downgrade not implemented")
