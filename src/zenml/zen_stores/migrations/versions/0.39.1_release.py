"""Release [0.39.1].

Revision ID: 0.39.1
Revises: 0.39.0
Create Date: 2023-05-10 10:57:00.777671

"""

# revision identifiers, used by Alembic.
revision = "0.39.1"
down_revision = "0.39.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
