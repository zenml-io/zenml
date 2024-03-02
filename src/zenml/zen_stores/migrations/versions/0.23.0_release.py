"""Release [0.23.0].

Revision ID: 0.23.0
Revises: 0.22.0
Create Date: 2022-12-02 12:26:39.020576

"""

# revision identifiers, used by Alembic.
revision = "0.23.0"
down_revision = "0.22.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
