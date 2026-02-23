"""add snapshot index [d1e8c2c4a9ef].

Revision ID: d1e8c2c4a9ef
Revises: 0e5c99d02aa7
Create Date: 2026-01-23 16:25:05.328420

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e8c2c4a9ef"
down_revision = "0e5c99d02aa7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.create_index(
            "ix_pipeline_snapshot_source_snapshot_id",
            ["source_snapshot_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("pipeline_snapshot", schema=None) as batch_op:
        batch_op.drop_index("ix_pipeline_snapshot_source_snapshot_id")
