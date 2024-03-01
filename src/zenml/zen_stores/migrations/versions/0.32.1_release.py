"""Release [0.32.1].

Revision ID: 0.32.1
Revises: 0.32.0
Create Date: 2023-01-26 17:22:22.494010

"""

# revision identifiers, used by Alembic.
revision = "0.32.1"
down_revision = "0.32.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
