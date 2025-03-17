"""add workspace display name [cbc6acd71f92].

Revision ID: cbc6acd71f92
Revises: 9e7bf0970266
Create Date: 2025-03-12 19:38:57.126846

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "cbc6acd71f92"
down_revision = "9e7bf0970266"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "display_name",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )

    # Migrate existing workspace names to display_name
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=("workspace",))
    workspace_table = sa.Table("workspace", meta)

    for workspace_id, workspace_name in connection.execute(
        sa.select(
            workspace_table.c.id,
            workspace_table.c.name,
        )
    ):
        connection.execute(
            sa.update(workspace_table)
            .where(workspace_table.c.id == workspace_id)
            .values(display_name=workspace_name)
        )

    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.alter_column(
            "display_name", existing_type=sa.String(50), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("workspace", schema=None) as batch_op:
        batch_op.drop_column("display_name")
