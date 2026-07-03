"""Add pipeline_run pipeline_id created index [c1d964b6075c].

Revision ID: c1d964b6075c
Revises: 0.95.1
Create Date: 2026-06-18 13:43:52.380599

"""

from zenml.zen_stores.migrations.utils import (
    create_index_if_missing,
    drop_index_if_exists,
)

# revision identifiers, used by Alembic.
revision = "c1d964b6075c"
down_revision = "0.95.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    create_index_if_missing(
        "pipeline_run",
        "ix_pipeline_run_pipeline_id_created",
        ["pipeline_id", "created"],
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    drop_index_if_exists("pipeline_run", "ix_pipeline_run_pipeline_id_created")
