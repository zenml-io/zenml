"""add sdk_docs_url to flavors [623a234c11f5].

Revision ID: 623a234c11f5
Revises: 0.34.0
Create Date: 2023-03-03 14:36:37.828842

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "623a234c11f5"
down_revision = "0.34.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "sdk_docs_url",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("flavor", schema=None) as batch_op:
        batch_op.drop_column("sdk_docs_url")
