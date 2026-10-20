"""Add payload backfill completion [ca69b60eed29].

Revision ID: ca69b60eed29
Revises: 6fce9968352d
Create Date: 2026-10-19 22:51:38.781322

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ca69b60eed29"
down_revision = "6fce9968352d"
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
