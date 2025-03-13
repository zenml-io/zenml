"""add stack description [f76a368a25a5].

Revision ID: f76a368a25a5
Revises: f1d723fd723b
Create Date: 2025-02-22 19:03:32.568076

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "f76a368a25a5"
down_revision = "f1d723fd723b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "description",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("stack", schema=None) as batch_op:
        batch_op.drop_column("description")
