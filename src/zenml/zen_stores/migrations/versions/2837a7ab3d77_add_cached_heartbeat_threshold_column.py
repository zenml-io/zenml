"""Add cached heartbeat threshold column [2837a7ab3d77].

Revision ID: 2837a7ab3d77
Revises: d203788f82b9
Create Date: 2025-11-28 12:27:14.341553

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2837a7ab3d77"
down_revision = "6e4eb89f632d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("heartbeat_threshold", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("heartbeat_threshold")
