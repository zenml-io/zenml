"""remove workspace from globals [3b1776345020].

Revision ID: 3b1776345020
Revises: 0392807467dc
Create Date: 2025-02-13 15:57:38.255825

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3b1776345020"
down_revision = "0392807467dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision.

    Raises:
        RuntimeError: If more than one workspace exists.
    """
    # If more than one workspace exists, we fail the migration because it
    # would mean merging together resources from different workspaces, which
    # can lead to naming conflicts.
    workspace_count_query = sa.text("SELECT COUNT(*) FROM workspace")
    connection = op.get_bind()
    workspace_count = connection.execute(
        workspace_count_query,
    ).scalar()
    assert isinstance(workspace_count, int)
    if workspace_count > 1:
        raise RuntimeError(
            "Your ZenML installation has more than just the default workspace "
            "configured. This migration removes the workspace scopes of all "
            "stacks, components, flavors, service connectors and secrets, "
            "which may lead to naming conflicts if multiple workspaces are "
            "present. Please delete all but the default workspace before "
            "running this migration."
        )

    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_flavor_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_secret_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_service_connector_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_stack_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_stack_component_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision.

    Raises:
        NotImplementedError: This migration is not reversible.
    """
    raise NotImplementedError("This migration is not reversible.")
