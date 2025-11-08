"""Add heartbeat column for step runs [a5a17015b681].

Revision ID: a5a17015b681
Revises: af27025fe19c
Create Date: 2025-10-13 12:24:12.470803

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a5a17015b681"
down_revision = "af27025fe19c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("latest_heartbeat", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("latest_heartbeat")
