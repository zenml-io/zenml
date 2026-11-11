"""Retain managed model dependencies.

Revision ID: 976d81482e19
Revises: 85e83c8f3bd5
"""

import sqlalchemy as sa
from alembic import op

revision = "976d81482e19"
down_revision = "85e83c8f3bd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Prevent dependency deletion until managed provider cleanup completes."""
    op.create_table(
        "managed_model_dependency",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_version_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_store_id", sa.Uuid(), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["managed_model_service.id"],
            name="fk_managed_dependency_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_version.id"],
            name="fk_managed_dependency_artifact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_store_id"],
            ["stack_component.id"],
            name="fk_managed_dependency_store",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["service_connector.id"],
            name="fk_managed_dependency_connector",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "service_id",
            "revision_id",
            "artifact_version_id",
            name="uq_managed_model_dependency",
        ),
    )
