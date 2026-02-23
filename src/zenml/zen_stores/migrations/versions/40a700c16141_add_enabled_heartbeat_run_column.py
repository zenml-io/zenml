"""Add enabled heartbeat run column [40a700c16141].

Revision ID: 40a700c16141
Revises: ff6b5e42a915
Create Date: 2026-01-08 11:17:31.820456

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "40a700c16141"
down_revision = "ff6b5e42a915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        # create nullable column
        batch_op.add_column(
            sa.Column("enable_heartbeat", sa.Boolean(), nullable=True)
        )

    # back-populate runs with False value
    connection = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=connection, only=["pipeline_run"])
    run_table = sa.Table("pipeline_run", meta)
    connection.execute(sa.update(run_table).values(enable_heartbeat=False))

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        # update to non-nullable column
        batch_op.alter_column(
            "enable_heartbeat", existing_type=sa.Boolean, nullable=False
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("enable_heartbeat")
