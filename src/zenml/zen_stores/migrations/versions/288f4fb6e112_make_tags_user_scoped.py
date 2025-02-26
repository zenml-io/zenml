"""make tags user scoped [288f4fb6e112].

Revision ID: 288f4fb6e112
Revises: 3b1776345020
Create Date: 2025-02-19 15:16:42.954792

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

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
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )

        # Add foreign key constraints
        batch_op.create_foreign_key(
            "fk_tag_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tag_user_id_user", type_="foreignkey")
        batch_op.drop_column("user_id")
