"""Pipeline snapshots [8ad841ad9bfe].

Revision ID: 8ad841ad9bfe
Revises: a71cca37e42d
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
down_revision = "a71cca37e42d"
branch_labels = None
depends_on = None


def rename_pipeline_deployment_to_pipeline_snapshot() -> None:
    """Rename the pipeline deployment table to pipeline snapshot."""
    # 1. Drop existing foreign keys referencing the pipeline deployment table
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_pipeline_run_deployment_id_pipeline_deployment",
            type_="foreignkey",
        )

    with op.batch_alter_table("run_template", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_run_template_source_deployment_id_pipeline_deployment",
            type_="foreignkey",
        )

    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_step_configuration_deployment_id_pipeline_deployment",
            type_="foreignkey",
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_step_run_deployment_id_pipeline_deployment", type_="foreignkey"
        )

    # 2. Drop foreign keys of the pipeline deployment tables themselves, which
    # we will have to rename
    with op.batch_alter_table("pipeline_deployment", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_pipeline_deployment_build_id_pipeline_build",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_code_reference_id_code_reference",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_pipeline_id_pipeline", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_project_id_project", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_schedule_id_schedule", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_stack_id_stack", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_pipeline_deployment_user_id_user", type_="foreignkey"
        )

    # 3. Rename table
    op.rename_table("pipeline_deployment", "pipeline_snapshot")

    # 4. Recreate foreign keys on the renamed table
    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_build_id_pipeline_build",
            "pipeline_build",
            ["build_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_code_reference_id_code_reference",
            "code_reference",
            ["code_reference_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_pipeline_id_pipeline",
            "pipeline",
            ["pipeline_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_schedule_id_schedule",
            "schedule",
            ["schedule_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_stack_id_stack",
            "stack",
            ["stack_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 5. Drop more constraints that need to be renamed, and alter the column
    # names. For some reason, we can't use the same `batch_alter_table` to
    # rename columns and then create new constraints, so we have to do it in
    # separate calls.
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_orchestrator_run_id_for_deployment_id", type_="unique"
        )

        batch_op.alter_column(
            "deployment_id",
            existing_type=sa.CHAR(length=32),
            new_column_name="snapshot_id",
        )

    with op.batch_alter_table("run_template", schema=None) as batch_op:
        batch_op.alter_column(
            "source_deployment_id",
            existing_type=sa.CHAR(length=32),
            new_column_name="source_snapshot_id",
        )

    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_step_name_for_deployment", type_="unique"
        )

        batch_op.alter_column(
            "deployment_id",
            existing_type=sa.CHAR(length=32),
            new_column_name="snapshot_id",
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.alter_column(
            "deployment_id",
            existing_type=sa.CHAR(length=32),
            new_column_name="snapshot_id",
        )

    # 6. Add back the constraints with correct columns and names
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_orchestrator_run_id_for_snapshot_id",
            ["snapshot_id", "orchestrator_run_id"],
        )
        batch_op.create_foreign_key(
            "fk_pipeline_run_snapshot_id_pipeline_snapshot",
            "pipeline_snapshot",
            ["snapshot_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("run_template", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_run_template_source_snapshot_id_pipeline_snapshot",
            "pipeline_snapshot",
            ["source_snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("step_configuration", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_step_name_for_snapshot", ["snapshot_id", "name"]
        )
        batch_op.create_foreign_key(
            "fk_step_configuration_snapshot_id_pipeline_snapshot",
            "pipeline_snapshot",
            ["snapshot_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_step_run_snapshot_id_pipeline_snapshot",
            "pipeline_snapshot",
            ["snapshot_id"],
            ["id"],
            ondelete="CASCADE",
        )


def add_unlisted_pipeline_if_necessary() -> None:
    """Create pipelines for orphaned snapshots without a pipeline reference."""
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(
        bind=connection, only=("pipeline_snapshot", "pipeline", "pipeline_run")
    )

    pipeline_snapshot_table = sa.Table("pipeline_snapshot", meta)
    pipeline_table = sa.Table("pipeline", meta)
    pipeline_run_table = sa.Table("pipeline_run", meta)

    projects_with_orphaned_snapshots = connection.execute(
        sa.select(
            pipeline_snapshot_table.c.project_id,
        )
        .where(pipeline_snapshot_table.c.pipeline_id.is_(None))
        .group_by(pipeline_snapshot_table.c.project_id)
    ).fetchall()

    if not projects_with_orphaned_snapshots:
        return

    now = utc_now()

    for project_id_row in projects_with_orphaned_snapshots:
        existing_pipeline = connection.execute(
            sa.select(pipeline_table.c.id)
            .where(pipeline_table.c.project_id == project_id_row.project_id)
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
                    description="Auto-created pipeline for snapshots without "
                    "pipeline reference",
                    project_id=project_id_row.project_id,
                    user_id=None,
                )
            )

        connection.execute(
            sa.update(pipeline_snapshot_table)
            .where(
                pipeline_snapshot_table.c.project_id
                == project_id_row.project_id
            )
            .where(pipeline_snapshot_table.c.pipeline_id.is_(None))
            .values(pipeline_id=unlisted_pipeline_id)
        )

        connection.execute(
            sa.update(pipeline_run_table)
            .where(
                pipeline_run_table.c.project_id == project_id_row.project_id
            )
            .where(pipeline_run_table.c.pipeline_id.is_(None))
            .values(pipeline_id=unlisted_pipeline_id)
        )


def migrate_run_templates() -> None:
    """Migrate run templates into the snapshot table."""
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(
        bind=connection,
        only=("pipeline_snapshot", "run_template", "tag_resource"),
    )

    pipeline_snapshot_table = sa.Table("pipeline_snapshot", meta)
    run_template_table = sa.Table("run_template", meta)
    tag_resource_table = sa.Table("tag_resource", meta)

    # Step 1: Update the `template_id` of snapshots to the source snapshot
    # id
    snapshot_template_mapping = connection.execute(
        sa.select(
            pipeline_snapshot_table.c.id,
            run_template_table.c.source_snapshot_id,
        )
        .outerjoin(
            run_template_table,
            run_template_table.c.id == pipeline_snapshot_table.c.template_id,
        )
        .where(pipeline_snapshot_table.c.template_id.is_not(None))
    ).fetchall()

    snapshot_updates = [
        {"id_": snapshot_id, "source_snapshot_id": source_snapshot_id}
        for snapshot_id, source_snapshot_id in snapshot_template_mapping
    ]
    if snapshot_updates:
        connection.execute(
            sa.update(pipeline_snapshot_table)
            .where(pipeline_snapshot_table.c.id == sa.bindparam("id_"))
            .values(source_snapshot_id=sa.bindparam("source_snapshot_id")),
            snapshot_updates,
        )

    # Step 2: Migrate tags from run templates to their source snapshots
    tag_run_template_mapping = connection.execute(
        sa.select(
            tag_resource_table.c.tag_id,
            run_template_table.c.source_snapshot_id,
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
            "resource_id": source_snapshot_id,
            "resource_type": "pipeline_snapshot",
        }
        for tag_id, source_snapshot_id in tag_run_template_mapping
    ]
    if tag_resource_insertions:
        op.bulk_insert(tag_resource_table, tag_resource_insertions)

    # Step 3: Migrate non-hidden run templates to their source snapshots
    # If there are multiple templates for the same source snapshot, use the
    # name/description of the latest one.
    latest_templates_subquery = (
        sa.select(
            run_template_table.c.source_snapshot_id,
            sa.func.max(run_template_table.c.created).label("created"),
        )
        .where(run_template_table.c.hidden.is_(False))
        .where(run_template_table.c.source_snapshot_id.is_not(None))
        .group_by(run_template_table.c.source_snapshot_id)
        .subquery()
    )
    latest_templates_query = sa.select(
        run_template_table.c.name,
        run_template_table.c.description,
        run_template_table.c.source_snapshot_id,
    ).join(
        latest_templates_subquery,
        sa.and_(
            latest_templates_subquery.c.source_snapshot_id
            == run_template_table.c.source_snapshot_id,
            run_template_table.c.created
            == latest_templates_subquery.c.created,
        ),
    )

    snapshot_updates = [
        {
            "id_": source_snapshot_id,
            "name": template_name,
            "description": template_description,
        }
        for template_name, template_description, source_snapshot_id in connection.execute(
            latest_templates_query
        ).fetchall()
    ]
    if snapshot_updates:
        connection.execute(
            sa.update(pipeline_snapshot_table)
            .where(pipeline_snapshot_table.c.id == sa.bindparam("id_"))
            .values(
                name=sa.bindparam("name"),
                description=sa.bindparam("description"),
            ),
            snapshot_updates,
        )


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    rename_pipeline_deployment_to_pipeline_snapshot()
    add_unlisted_pipeline_if_necessary()

    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "name", sqlmodel.sql.sqltypes.AutoString(), nullable=True
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
            "fk_pipeline_snapshot_pipeline_id_pipeline", type_="foreignkey"
        )
        batch_op.alter_column(
            "pipeline_id", existing_type=sa.CHAR(length=32), nullable=False
        )
        batch_op.create_unique_constraint(
            "unique_name_for_pipeline_id", ["pipeline_id", "name"]
        )
        batch_op.create_foreign_key(
            "fk_pipeline_snapshot_pipeline_id_pipeline",
            "pipeline",
            ["pipeline_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.add_column(
            sa.Column(
                "source_snapshot_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "triggered_by", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "triggered_by_type",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )

    migrate_run_templates()


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: Downgrade not implemented.
    """
    raise NotImplementedError("Downgrade not implemented")
