"""make workspace optional [3b1776345020].

Revision ID: 3b1776345020
Revises: 0.74.0
Create Date: 2025-02-13 15:57:38.255825

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3b1776345020"
down_revision = "0.74.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=True
        )

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=True
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=True
        )

    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=True
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("stack_component", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=False
        )

    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=False
        )

    with op.batch_alter_table("service_connector", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=False
        )

    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "workspace_id", existing_type=sa.CHAR(length=32), nullable=False
        )
