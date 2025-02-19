"""make tags workspace scoped [288f4fb6e112].

Revision ID: 288f4fb6e112
Revises: 3b1776345020
Create Date: 2025-02-19 15:16:42.954792

"""

import os

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.sql import column, table

from zenml.constants import (
    DEFAULT_WORKSPACE_NAME,
    ENV_ZENML_DEFAULT_WORKSPACE_NAME,
)

# revision identifiers, used by Alembic.
revision = "288f4fb6e112"
down_revision = "3b1776345020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("tag", schema=None) as batch_op:
        # First add columns as nullable
        batch_op.add_column(
            sa.Column(
                "workspace_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )

    # Create a temp table object for the update
    tag_table = table(
        "tag",
        column("id", sqlmodel.sql.sqltypes.GUID()),
        column("workspace_id", sqlmodel.sql.sqltypes.GUID()),
    )

    default_workspace_name = os.getenv(
        ENV_ZENML_DEFAULT_WORKSPACE_NAME, DEFAULT_WORKSPACE_NAME
    )

    # Get the default workspace ID (you'll need to implement this logic)
    # This is a placeholder - you need to determine how to get the default workspace ID
    default_workspace_query = sa.text(
        "SELECT id FROM workspace WHERE name = :default_workspace_name LIMIT 1"
    )
    connection = op.get_bind()
    default_workspace_id = connection.execute(
        default_workspace_query,
        {"default_workspace_name": default_workspace_name},
    ).scalar()

    if default_workspace_id is None:
        raise Exception(
            "Default workspace not found. Cannot proceed with migration."
        )

    # Update existing records with the default workspace
    op.execute(tag_table.update().values(workspace_id=default_workspace_id))

    # Now make workspace_id non-nullable
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id",
            existing_type=sqlmodel.sql.sqltypes.GUID(),
            nullable=False,
        )

        # Add foreign key constraints
        batch_op.create_foreign_key(
            "fk_tag_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_tag_workspace_id_workspace",
            "workspace",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_tag_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_tag_user_id_user", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("workspace_id")
