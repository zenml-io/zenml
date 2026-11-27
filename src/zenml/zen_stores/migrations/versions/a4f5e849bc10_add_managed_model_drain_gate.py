"""Add managed model drain gate and retry scheduling.

Revision ID: a4f5e849bc10
Revises: 976d81482e19
"""

import sqlalchemy as sa
from alembic import op

revision = "a4f5e849bc10"
down_revision = "976d81482e19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a durable workspace admission gate and operation retry timestamp."""
    op.create_table(
        "managed_model_workspace",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("admission_open", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "managed_model_operation",
        sa.Column("available_at", sa.DateTime(), nullable=True),
    )
