"""Add stop mode to pipeline runs [a8d3e1c47f02].

Revision ID: a8d3e1c47f02
Revises: 8d638fcb4bd5
Create Date: 2026-11-03 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8d3e1c47f02"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "stop_mode",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("stop_mode")
