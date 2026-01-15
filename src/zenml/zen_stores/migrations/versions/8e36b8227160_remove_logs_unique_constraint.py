"""remove logs unique constraint [8e36b8227160].

Revision ID: 8e36b8227160
Revises: 0.93.1
Create Date: 2026-01-15 17:31:19.491562

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8e36b8227160"
down_revision = "0.93.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_constraint(
            "unique_source_per_run_and_step", type_="unique"
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
