"""add unique name constraints [1f9d1cd00b90].

Revision ID: 1f9d1cd00b90
Revises: f76a368a25a5
Create Date: 2025-02-22 20:18:34.258987

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "1f9d1cd00b90"
down_revision = "f76a368a25a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_action_name_in_workspace", ["name", "workspace_id"]
        )

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_api_key_name_in_service_account",
            ["name", "service_account_id"],
        )

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.drop_constraint("unique_artifact_name", type_="unique")
        batch_op.create_unique_constraint(
            "unique_artifact_name_in_workspace", ["name", "workspace_id"]
        )

    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_code_repository_name_in_workspace",
            ["name", "workspace_id"],
        )

    with op.batch_alter_table("event_source", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_event_source_name_in_workspace", ["name", "workspace_id"]
        )

    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_flavor_name_and_type", ["name", "type"]
        )

    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_schedule_name_in_workspace", ["name", "workspace_id"]
        )

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_secret_name_private_scope_user",
            ["name", "private", "user_id"],
        )

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_service_connector_name", ["name"]
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_stack_name", ["name"])

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_component_name_and_type", ["name", "type"]
        )

    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_tag_name", ["name"])

    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_trigger_name_in_workspace", ["name", "workspace_id"]
        )

    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.create_unique_constraint("unique_workspace_name", ["name"])


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.drop_constraint("unique_workspace_name", type_="unique")

    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_trigger_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_tag_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_component_name_and_type", type_="unique"
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.drop_constraint("unique_stack_name", type_="unique")

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_service_connector_name", type_="unique"
        )

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_secret_name_and_private_scope", type_="unique"
        )

    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_schedule_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.drop_constraint("unique_flavor_name_and_type", type_="unique")

    with op.batch_alter_table("event_source", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_event_source_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("code_repository", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_code_repository_name_in_workspace", type_="unique"
        )

    with op.batch_alter_table("artifact", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_artifact_name_in_workspace", type_="unique"
        )
        batch_op.create_unique_constraint("unique_artifact_name", ["name"])

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_api_key_name_in_service_account", type_="unique"
        )

    with op.batch_alter_table("action", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_action_name_in_workspace", type_="unique"
        )
