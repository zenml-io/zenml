"""remove logs log_key column [e6dfd46db163].

Revision ID: e6dfd46db163
Revises: 0.94.2
Create Date: 2026-04-15 14:58:30.098379

Drops ``unique_log_key`` and the ``log_key`` column. Log rows are still keyed by
``id`` and linked via ``pipeline_run_id`` / ``step_run_id`` and ``source``.

Downgrade restores the column (nullable) and the unique constraint; it will fail
if the application created duplicate synthetic keys that the old constraint
would reject (unlikely immediately after upgrade).
"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "e6dfd46db163"
down_revision = "0.94.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_constraint("unique_log_key", type_="unique")
        batch_op.drop_column("log_key")


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "log_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )
        batch_op.create_unique_constraint("unique_log_key", ["log_key"])
