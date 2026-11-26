"""Add pipeline_run.lane_half_applied, then fail [f3a6b0a11f01].

Labs lane negative test (F3a, AC6b): deliberately broken, never merge. The ADD COLUMN is committed on
MySQL before the error, so the database is left half-applied at the old Alembic revision.

Revision ID: f3a6b0a11f01
Revises: 0.99.0
Create Date: 2026-11-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a6b0a11f01"
down_revision = "0.99.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create a table and add a column, then fail on purpose so the zenml migration Job fails half-way."""
    op.create_table("lane_half_applied", sa.Column("id", sa.Integer(), primary_key=True))
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("lane_half_applied", sa.Integer(), nullable=True))
    raise RuntimeError("F3a AC6b: deliberate half-applied MySQL migration (Labs lane negative test)")


def downgrade() -> None:
    """Remove the column and the table."""
    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_column("lane_half_applied")
    op.drop_table("lane_half_applied")
