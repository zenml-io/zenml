"""Add stop criteria columns to trigger table [e2f4c6a9d1b3].

Revision ID: e2f4c6a9d1b3
Revises: 9306debdfe0c
Create Date: 2026-04-24 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e2f4c6a9d1b3"
down_revision = "9306debdfe0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.add_column(sa.Column("end_time", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("max_runs", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_column("max_runs")
        batch_op.drop_column("end_time")
