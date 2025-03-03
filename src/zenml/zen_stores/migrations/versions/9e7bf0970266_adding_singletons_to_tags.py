"""adding singletons to tags [9e7bf0970266].

Revision ID: 9e7bf0970266
Revises: 0.75.0
Create Date: 2025-03-03 15:17:49.341208

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9e7bf0970266"
down_revision = "0.75.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.add_column(
        "tag",
        sa.Column(
            "singleton",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_column("tag", "singleton")
