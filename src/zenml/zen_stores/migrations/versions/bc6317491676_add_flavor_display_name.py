"""add flavor display_name [bc6317491676].

Revision ID: bc6317491676
Revises: 0.91.2
Create Date: 2025-11-20 16:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "bc6317491676"
down_revision = "0.91.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "display_name",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.drop_column("display_name")
