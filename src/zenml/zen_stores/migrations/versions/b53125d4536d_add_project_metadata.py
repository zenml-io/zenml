"""Add project metadata [b53125d4536d].

Revision ID: b53125d4536d
Revises: b6f2a8d9c3e1
Create Date: 2026-07-16 15:49:35.390499

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "b53125d4536d"
down_revision = "b6f2a8d9c3e1"
branch_labels = None
depends_on = None

PROJECT_METADATA_TYPE = sa.String(length=16777215).with_variant(
    mysql.MEDIUMTEXT, "mysql"
)


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "project_metadata",
                PROJECT_METADATA_TYPE,
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_column("project_metadata")
