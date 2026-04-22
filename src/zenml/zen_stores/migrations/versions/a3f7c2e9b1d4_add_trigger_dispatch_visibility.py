"""Add trigger dispatch visibility columns [a3f7c2e9b1d4].

Revision ID: a3f7c2e9b1d4
Revises: e6dfd46db163
Create Date: 2026-04-17

"""

import sqlalchemy as sa
from alembic import op

revision = "a3f7c2e9b1d4"
down_revision = "e6dfd46db163"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    with op.batch_alter_table("trigger_snapshot", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "dispatch_state",
                sa.String(length=65535).with_variant(sa.TEXT(), "mysql"),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema."""
    with op.batch_alter_table("trigger_snapshot", schema=None) as batch_op:
        batch_op.drop_column("dispatch_state")
