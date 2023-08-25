"""this is a dummy migration [21695de7acbe].

Revision ID: 21695de7acbe
Revises: 0.43.0
Create Date: 2023-08-25 15:05:13.989253

"""
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21695de7acbe'
down_revision = '0.43.0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    pass


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
