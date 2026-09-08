"""Add project retention settings [8b2d4e6f901a].

Revision ID: 8b2d4e6f901a
Revises: 7a1c3d9e2b4f
Create Date: 2026-09-08 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "8b2d4e6f901a"
down_revision = "7a1c3d9e2b4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable settings without enabling retention or backfilling rows."""
    # Appended nullable columns qualify for instant DDL on supported MySQL 8
    # tables. MySQL 5.7 and unsupported table layouts may rebuild the table.
    with op.batch_alter_table("project") as batch_op:
        batch_op.add_column(
            sa.Column("retention_settings", sa.TEXT(), nullable=True)
        )


def downgrade() -> None:
    """Remove the retention settings column."""
    # Rebuilding project on SQLite can cascade-delete its dependent rows.
    # Native DROP requires SQLite 3.35+; older versions fail without data loss.
    op.drop_column("project", "retention_settings")
