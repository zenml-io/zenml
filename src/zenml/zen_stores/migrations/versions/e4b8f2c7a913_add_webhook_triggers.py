"""Add webhook triggers [e4b8f2c7a913].

Revision ID: e4b8f2c7a913
Revises: 7c0d9e4a1b2f
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "e4b8f2c7a913"
down_revision = "7c0d9e4a1b2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the webhook association to triggers."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.add_column(sa.Column("webhook_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_trigger_webhook_id_webhook",
            "webhook",
            ["webhook_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_trigger_type_webhook_id",
            ["type", "webhook_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove the webhook association from triggers."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_index("ix_trigger_type_webhook_id")
        batch_op.drop_constraint(
            "fk_trigger_webhook_id_webhook",
            type_="foreignkey",
        )
        batch_op.drop_column("webhook_id")
