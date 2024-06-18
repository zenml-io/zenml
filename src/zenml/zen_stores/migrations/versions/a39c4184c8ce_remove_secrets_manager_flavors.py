"""remove secrets manager flavors [a39c4184c8ce].

Revision ID: a39c4184c8ce
Revises: 0.53.0
Create Date: 2023-12-21 10:51:16.919710

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a39c4184c8ce"
down_revision = "0.53.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(only=("flavor",), bind=op.get_bind())
    flavors = sa.Table("flavor", meta)

    # Remove all secrets manager flavors
    conn.execute(flavors.delete().where(flavors.c.type == "secrets_manager"))


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
