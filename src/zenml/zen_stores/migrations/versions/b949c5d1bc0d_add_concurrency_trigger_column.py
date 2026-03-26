"""Add concurrency trigger column [b949c5d1bc0d].

Revision ID: b949c5d1bc0d
Revises: 3855b5d051cd
Create Date: 2026-02-18 10:46:09.881375

"""

import sqlalchemy as sa
from alembic import op

from zenml.enums import TriggerRunConcurrency

# revision identifiers, used by Alembic.
revision = "b949c5d1bc0d"
down_revision = "3855b5d051cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("concurrency", sa.VARCHAR(length=20), nullable=True)
        )

    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=["trigger"])
    trigger_table = sa.Table("trigger", meta)
    connection.execute(
        sa.update(trigger_table).values(
            concurrency=TriggerRunConcurrency.SKIP.value
        )
    )

    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.alter_column(
            "concurrency", existing_type=sa.VARCHAR(length=20), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("trigger", schema=None) as batch_op:
        batch_op.drop_column("concurrency")
