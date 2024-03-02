"""Release [0.30.0].

Revision ID: 0.30.0
Revises: 7834208cc3f6
Create Date: 2022-12-09 15:46:03.980591

"""

# revision identifiers, used by Alembic.
revision = "0.30.0"
down_revision = "7834208cc3f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
