"""add log stores [5c0a1c787128].

Revision ID: 5c0a1c787128
Revises: 0.91.2
Create Date: 2025-10-24 10:06:54.402219

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "5c0a1c787128"
down_revision = "0.92.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "log_store_id", sqlmodel.sql.sqltypes.GUID(), nullable=True
            )
        )
        batch_op.alter_column("uri", existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column(
            "artifact_store_id",
            existing_type=sa.CHAR(length=32),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_logs_log_store_id_stack_component",
            "stack_component",
            ["log_store_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("logs", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_logs_log_store_id_stack_component", type_="foreignkey"
        )
        batch_op.alter_column(
            "artifact_store_id",
            existing_type=sa.CHAR(length=32),
            nullable=False,
        )
        batch_op.alter_column("uri", existing_type=sa.TEXT(), nullable=False)
        batch_op.drop_column("log_store_id")
