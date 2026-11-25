"""Add token revocation state [b6f2a8d9c3e1].

Revision ID: b6f2a8d9c3e1
Revises: 0.96.1
Create Date: 2026-07-02 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b6f2a8d9c3e1"
down_revision = "0.96.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("password_changed_at", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("key_generation", sa.Integer(), nullable=True)
        )

    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(bind=connection, only=["api_key"])
    api_key_table = sa.Table("api_key", meta)

    connection.execute(sa.update(api_key_table).values(key_generation=1))

    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.alter_column(
            "key_generation", existing_type=sa.Integer, nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.drop_column("key_generation")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("password_changed_at")
