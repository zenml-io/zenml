"""increase secret values to MEDIUMTEXT on MySQL [f2c8e4a1903b].

Revision ID: f2c8e4a1903b
Revises: 0.94.3
Create Date: 2026-04-24 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "f2c8e4a1903b"
down_revision = "0.94.3"
branch_labels = None
depends_on = None

_MEDIUM_STRING = sa.String(length=16777215).with_variant(
    mysql.MEDIUMTEXT, "mysql"
)


def upgrade() -> None:
    """Widen `secret.values` (MySQL: TEXT to MEDIUMTEXT; other engines: see type)."""
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "values",
            existing_type=sa.TEXT(),
            type_=_MEDIUM_STRING,
            existing_nullable=True,
        )


def downgrade() -> None:
    """Narrow `secret.values` back to unbounded TEXT-style storage."""
    with op.batch_alter_table("secret", schema=None) as batch_op:
        batch_op.alter_column(
            "values",
            existing_type=_MEDIUM_STRING,
            type_=sa.TEXT(),
            existing_nullable=True,
        )
