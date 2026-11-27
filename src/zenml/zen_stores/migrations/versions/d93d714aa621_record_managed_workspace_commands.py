"""Record ordered managed workspace command receipts.

Revision ID: d93d714aa621
Revises: c4db519d2331
"""

import sqlalchemy as sa
from alembic import op

revision = "d93d714aa621"
down_revision = "c4db519d2331"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Preserve admission state and initialize the platform command sequence."""
    op.add_column(
        "managed_model_workspace",
        sa.Column(
            "command_receipt",
            sa.Text(),
            nullable=False,
            server_default=sa.text("('{}')"),
        ),
    )
