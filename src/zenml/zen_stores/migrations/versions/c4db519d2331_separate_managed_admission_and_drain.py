"""Separate managed admission closure from destructive drain.

Revision ID: c4db519d2331
Revises: 0aad3a9c8aa0
"""

import sqlalchemy as sa
from alembic import op

revision = "c4db519d2331"
down_revision = "0aad3a9c8aa0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Preserve existing drain intent and add ownership for ordinary disable."""
    op.add_column(
        "managed_model_workspace",
        sa.Column(
            "drain_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "managed_model_workspace",
        sa.Column("transition_id", sa.Uuid(), nullable=True),
    )
    gates = sa.table(
        "managed_model_workspace",
        sa.column("admission_open", sa.Boolean()),
        sa.column("drain_requested", sa.Boolean()),
    )
    op.execute(
        gates.update()
        .where(gates.c.admission_open.is_(False))
        .values(drain_requested=True)
    )
