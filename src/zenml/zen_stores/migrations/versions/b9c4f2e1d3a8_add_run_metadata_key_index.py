"""Add run metadata key index [b9c4f2e1d3a8].

Revision ID: b9c4f2e1d3a8
Revises: 0.94.4
Create Date: 2026-05-27 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b9c4f2e1d3a8"
down_revision = "0.94.4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        batch_op.create_index("ix_run_metadata_key", ["key"], unique=False)


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("run_metadata", schema=None) as batch_op:
        batch_op.drop_index("ix_run_metadata_key")
