"""Add artifact version availability [d4e8a1f5c2b7].

Revision ID: d4e8a1f5c2b7
Revises: b6f2a8d9c3e1
Create Date: 2026-07-14 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d4e8a1f5c2b7"
down_revision = "b6f2a8d9c3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("availability", sa.TEXT(), nullable=True)
        )

    connection = op.get_bind()

    meta = sa.MetaData()
    meta.reflect(bind=connection, only=["artifact_version"])
    artifact_version_table = sa.Table("artifact_version", meta)

    connection.execute(
        sa.update(artifact_version_table).values(availability="available")
    )

    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.alter_column(
            "availability", existing_type=sa.TEXT(), nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("artifact_version", schema=None) as batch_op:
        batch_op.drop_column("availability")
