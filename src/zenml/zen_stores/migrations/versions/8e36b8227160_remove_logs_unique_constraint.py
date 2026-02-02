"""remove logs unique constraint [8e36b8227160].

Revision ID: 8e36b8227160
Revises: 0.93.2
Create Date: 2026-01-15 17:31:19.491562

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "8e36b8227160"
down_revision = "0.93.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
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
                "log_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.create_unique_constraint("unique_log_key", ["log_key"])
        batch_op.drop_constraint(
            "unique_source_per_run_and_step", type_="unique"
        )

    connection = op.get_bind()
    logs = sa.table(
        "logs",
        sa.column("project_id"),
        sa.column("user_id"),
        sa.column("step_run_id"),
        sa.column("pipeline_run_id"),
    )
    step_run = sa.table(
        "step_run",
        sa.column("id"),
        sa.column("project_id"),
        sa.column("user_id"),
    )
    pipeline_run = sa.table(
        "pipeline_run",
        sa.column("id"),
        sa.column("project_id"),
        sa.column("user_id"),
    )

    connection.execute(
        sa.update(logs)
        .where(logs.c.step_run_id.is_not(None))
        .values(
            project_id=sa.select(step_run.c.project_id)
            .where(step_run.c.id == logs.c.step_run_id)
            .scalar_subquery(),
            user_id=sa.select(step_run.c.user_id)
            .where(step_run.c.id == logs.c.step_run_id)
            .scalar_subquery(),
        )
    )

    connection.execute(
        sa.update(logs)
        .where(logs.c.step_run_id.is_(None))
        .where(logs.c.pipeline_run_id.is_not(None))
        .values(
            project_id=sa.select(pipeline_run.c.project_id)
            .where(pipeline_run.c.id == logs.c.pipeline_run_id)
            .scalar_subquery(),
            user_id=sa.select(pipeline_run.c.user_id)
            .where(pipeline_run.c.id == logs.c.pipeline_run_id)
            .scalar_subquery(),
        )
    )

    connection.execute(sa.delete(logs).where(logs.c.project_id.is_(None)))

    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_logs_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_logs_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_logs_user_id_user", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_logs_project_id_project", type_="foreignkey"
        )
        batch_op.drop_constraint("unique_log_key", type_="unique")
        batch_op.drop_column("log_key")
        batch_op.drop_column("user_id")
        batch_op.drop_column("project_id")
        batch_op.create_unique_constraint(
            "unique_source_per_run_and_step",
            ["source", "pipeline_run_id", "step_run_id"],
        )
