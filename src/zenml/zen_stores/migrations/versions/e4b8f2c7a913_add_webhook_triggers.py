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
    """Add the webhook integration association to triggers."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("webhook_integration_id", sa.Uuid(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_trigger_webhook_integration_id_webhook_integration",
            "webhook_integration",
            ["webhook_integration_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_trigger_type_webhook_integration_id",
            ["type", "webhook_integration_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove the webhook integration association from triggers."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_index("ix_trigger_type_webhook_integration_id")
        batch_op.drop_constraint(
            "fk_trigger_webhook_integration_id_webhook_integration",
            type_="foreignkey",
        )
        batch_op.drop_column("webhook_integration_id")
