"""Add is_archived column for schedules [ff6b5e42a915].

Revision ID: ff6b5e42a915
Revises: 514b9fae1500
Create Date: 2025-12-12 11:05:11.954042

"""

import sqlalchemy as sa
from alembic import op

revision = "ff6b5e42a915"
down_revision = "0.93.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_archived", sa.Boolean(), nullable=True)
        )

    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(bind=connection, only=["schedule"])
    schedule_table = sa.Table("schedule", meta)

    connection.execute(sa.update(schedule_table).values(is_archived=False))

    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.alter_column(
            "is_archived", existing_type=sa.Boolean, nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("schedule", schema=None) as batch_op:
        batch_op.drop_column("is_archived")
