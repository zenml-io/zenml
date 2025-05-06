"""add secret private attr [f1d723fd723b].

Revision ID: f1d723fd723b
Revises: 288f4fb6e112
Create Date: 2025-02-21 19:40:14.596681

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f1d723fd723b"
down_revision = "288f4fb6e112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    # Step 1: Add private column as nullable
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.add_column(sa.Column("private", sa.Boolean(), nullable=True))

    # Step 2: Update existing records based on scope
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE secret SET private = TRUE WHERE scope = 'user';")
    )
    connection.execute(
        sa.text("UPDATE secret SET private = FALSE WHERE scope != 'user';")
    )

    # Step 3: Make private column non-nullable and drop scope
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "private", existing_type=sa.Boolean(), nullable=False
        )
        batch_op.drop_column("scope")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scope", sa.VARCHAR(), nullable=True))

    # Restore scope values based on private flag
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE secret SET scope = 'user' WHERE private = TRUE;")
    )
    connection.execute(
        sa.text("UPDATE secret SET scope = 'workspace' WHERE private = FALSE;")
    )

    # Make scope non-nullable and drop private
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "scope", existing_type=sa.VARCHAR(), nullable=False
        )
        batch_op.drop_column("private")
