"""Add managed model service operations.

Revision ID: 85e83c8f3bd5
Revises: 8d638fcb4bd5
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

revision = "85e83c8f3bd5"
down_revision = "8d638fcb4bd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add durable service documents and idempotent execution records."""
    op.create_table(
        "managed_model_service",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("model_deployer_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column(
            "document",
            sa.Text().with_variant(MEDIUMTEXT(), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "resources",
            sa.Text().with_variant(MEDIUMTEXT(), "mysql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_managed_model_service_project_id_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_deployer_id"],
            ["stack_component.id"],
            name="fk_managed_model_service_model_deployer_id_stack_component",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "managed_model_operation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("target_revision_id", sa.Uuid(), nullable=True),
        sa.Column("lease_id", sa.Uuid(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "checkpoint",
            sa.Text().with_variant(MEDIUMTEXT(), "mysql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["managed_model_service.id"],
            name="fk_managed_model_operation_service_id_managed_model_service",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "request_key", name="uq_managed_model_request"
        ),
    )
    op.create_index(
        "ix_managed_model_operation_project_id",
        "managed_model_operation",
        ["project_id"],
    )
    op.create_index(
        "ix_managed_model_operation_status",
        "managed_model_operation",
        ["status"],
    )


def downgrade() -> None:
    """Downgrades are not supported by the workspace migration contract."""
