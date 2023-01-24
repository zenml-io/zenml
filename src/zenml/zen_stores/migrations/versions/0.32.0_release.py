"""Release [0.32.0].

Revision ID: 0.32.0
Revises: 0.31.1
Create Date: 2023-01-23 19:40:47.713699

"""


# revision identifiers, used by Alembic.
revision = "0.32.0"
down_revision = "0.31.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
