"""Add pipeline_run triggered_by index [c033e0f0f0d0].

Revision ID: c033e0f0f0d0
Revises: c1d964b6075c
Create Date: 2026-06-25 12:04:34.959049

"""

from zenml.zen_stores.migrations.utils import (
    create_index_if_missing,
    drop_index_if_exists,
)

# revision identifiers, used by Alembic.
revision = "c033e0f0f0d0"
down_revision = "c1d964b6075c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    create_index_if_missing(
        "pipeline_run",
        "ix_pipeline_run_triggered_by_triggered_by_type",
        ["triggered_by", "triggered_by_type"],
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    drop_index_if_exists(
        "pipeline_run", "ix_pipeline_run_triggered_by_triggered_by_type"
    )
