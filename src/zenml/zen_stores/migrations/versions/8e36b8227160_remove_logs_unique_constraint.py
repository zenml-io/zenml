"""remove logs unique constraint [8e36b8227160].

Revision ID: 8e36b8227160
Revises: 0.93.1
Create Date: 2026-01-15 17:31:19.491562

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "8e36b8227160"
down_revision = "0e5c99d02aa7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "log_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.create_unique_constraint("unique_log_key", ["log_key"])
        batch_op.drop_constraint(
            "unique_source_per_run_and_step", type_="unique"
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_column("log_key")
        batch_op.drop_constraint("unique_log_key", type_="unique")
