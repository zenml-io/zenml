"""Rename webhook integration resources [b7e1f3a9c204].

Revision ID: b7e1f3a9c204
Revises: e4b8f2c7a913
Create Date: 2026-08-27
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "b7e1f3a9c204"
down_revision = "e4b8f2c7a913"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename legacy webhook integration tables and trigger references."""
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "webhook_integration" in tables and "webhook" not in tables:
        op.rename_table("webhook_integration", "webhook")
    if "webhook_integration_stats" in tables and "webhook_stats" not in tables:
        op.rename_table("webhook_integration_stats", "webhook_stats")

    trigger_columns = {
        column["name"] for column in inspector.get_columns("trigger")
    }
    if "webhook_integration_id" in trigger_columns:
        with op.batch_alter_table("trigger", schema=None) as batch_op:
            batch_op.alter_column(
                "webhook_integration_id",
                new_column_name="webhook_id",
                existing_type=sa.Uuid(),
                existing_nullable=True,
            )

    connection = op.get_bind()
    webhook_triggers = connection.execute(
        sa.text("SELECT id, configuration FROM trigger WHERE type = :type"),
        {"type": "webhook"},
    ).mappings()
    for trigger in webhook_triggers:
        stored = json.loads(trigger["configuration"])
        if "configuration" in stored:
            configuration = stored
        else:
            configuration = {
                "configuration": {"target_events": stored.get("events", [])}
            }
        connection.execute(
            sa.text(
                "UPDATE trigger SET flavor = :flavor, "
                "configuration = :configuration WHERE id = :id"
            ),
            {
                "id": trigger["id"],
                "flavor": "webhook",
                "configuration": json.dumps(configuration),
            },
        )


def downgrade() -> None:
    """Restore legacy webhook integration terminology."""
    inspector = sa.inspect(op.get_bind())
    trigger_columns = {
        column["name"] for column in inspector.get_columns("trigger")
    }
    if "webhook_id" in trigger_columns:
        with op.batch_alter_table("trigger", schema=None) as batch_op:
            batch_op.alter_column(
                "webhook_id",
                new_column_name="webhook_integration_id",
                existing_type=sa.Uuid(),
                existing_nullable=True,
            )

    tables = set(inspector.get_table_names())
    if "webhook_stats" in tables:
        op.rename_table("webhook_stats", "webhook_integration_stats")
    if "webhook" in tables:
        op.rename_table("webhook", "webhook_integration")
