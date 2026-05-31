"""Add step run resource request id [d4e8f1a2b3c5].

Revision ID: d4e8f1a2b3c5
Revises: 0.94.4
Create Date: 2026-05-29 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e8f1a2b3c5"
down_revision = "0.94.4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "resource_request_id",
                sqlmodel.sql.sqltypes.GUID(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_column("resource_request_id")
