"""adding in_progress to runs [502b4fa5fa88].

Revision ID: 502b4fa5fa88
Revises: 83ef3cb746a5
Create Date: 2025-09-03 14:49:39.767249

"""

import sqlalchemy as sa
from alembic import op

from zenml.enums import ExecutionStatus

# revision identifiers, used by Alembic.
revision = "502b4fa5fa88"
down_revision = "83ef3cb746a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("in_progress", sa.Boolean(), nullable=True)
        )

    finished_statuses = ", ".join(
        f"'{status}'" for status in ExecutionStatus if status.is_finished
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(f"""
            UPDATE pipeline_run 
            SET in_progress = CASE 
                WHEN status IN ({finished_statuses}) THEN false 
                ELSE true 
            END
        """)  # nosec
    )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.alter_column(
            "in_progress", existing_type=sa.Boolean(), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("in_progress")
