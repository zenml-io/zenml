"""Add managed model inference key hash.

Revision ID: f0ff77a22aef
Revises: a4f5e849bc10
"""

import sqlalchemy as sa
from alembic import op

revision = "f0ff77a22aef"
down_revision = "a4f5e849bc10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Leave existing services locked until an inference key is issued."""
    op.add_column(
        "managed_model_service",
        sa.Column("inference_key_hash", sa.String(64), nullable=True),
    )
