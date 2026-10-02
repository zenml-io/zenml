"""Add payload backfill completion [79c3ad0f5f88].

Revision ID: 79c3ad0f5f88
Revises: bfb054a5101d
Create Date: 2026-09-28 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "79c3ad0f5f88"
down_revision = "bfb054a5101d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payload_backfill_completed", sa.DateTime(), nullable=True
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("server_settings", schema=None) as batch_op:
        batch_op.drop_column("payload_backfill_completed")
