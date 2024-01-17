"""Release [0.21.1].

Revision ID: 0.21.1
Revises: 0.21.0
Create Date: 2022-11-04 17:24:11.499869

"""


# revision identifiers, used by Alembic.
revision = "0.21.1"
down_revision = "0.21.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
