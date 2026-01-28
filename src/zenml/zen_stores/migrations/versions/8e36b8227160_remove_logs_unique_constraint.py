"""remove logs unique constraint [8e36b8227160].

Revision ID: 8e36b8227160
Revises: 0.93.1
Create Date: 2026-01-15 17:31:19.491562

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "8e36b8227160"
down_revision = "d1e8c2c4a9ef"
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

    # Prefer inferring scope from step runs when available, since a step run
    # always belongs to a single pipeline run.
    connection.execute(
        sa.text("""
            UPDATE logs
            SET
                project_id = (
                    SELECT project_id
                    FROM step_run
                    WHERE step_run.id = logs.step_run_id
                ),
                user_id = (
                    SELECT user_id
                    FROM step_run
                    WHERE step_run.id = logs.step_run_id
                )
            WHERE step_run_id IS NOT NULL
        """)
    )

    # Fall back to pipeline run scoping for rows not linked to a step run.
    connection.execute(
        sa.text("""
            UPDATE logs
            SET
                project_id = (
                    SELECT project_id
                    FROM pipeline_run
                    WHERE pipeline_run.id = logs.pipeline_run_id
                ),
                user_id = COALESCE(
                    logs.user_id,
                    (
                        SELECT user_id
                        FROM pipeline_run
                        WHERE pipeline_run.id = logs.pipeline_run_id
                    )
                )
            WHERE project_id IS NULL AND pipeline_run_id IS NOT NULL
        """)
    )

    # If we cannot infer a project for a log entry, it cannot be kept because
    # the logs table is project-scoped.
    connection.execute(
        sa.text("""
            DELETE FROM logs
            WHERE project_id IS NULL
        """)
    )

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
