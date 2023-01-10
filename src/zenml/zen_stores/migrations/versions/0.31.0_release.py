"""Release [0.31.0].

Revision ID: 0.31.0
Revises: 248dfd320b68
Create Date: 2022-12-23 16:05:04.535949

"""


# revision identifiers, used by Alembic.
revision = "0.31.0"
down_revision = "248dfd320b68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
