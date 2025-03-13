"""add user default workspace [2e695a26fe7a].

Revision ID: 2e695a26fe7a
Revises: 1f9d1cd00b90
Create Date: 2025-02-24 18:19:43.121393

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "2e695a26fe7a"
down_revision = "1f9d1cd00b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "default_workspace_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_user_default_workspace_id_workspace",
            "workspace",
            ["default_workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_user_default_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("default_workspace_id")
