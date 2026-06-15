"""add resource pools [b0ba2c3800e3].

Revision ID: b0ba2c3800e3
Revises: 0.94.2
Create Date: 2026-03-26 10:01:45.886453

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "b0ba2c3800e3"
down_revision = "0.94.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        "resource_pool",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_resource_pool_user_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="unique_resource_pool_name"),
    )
    op.create_table(
        "resource_pool_resource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("pool_id", sa.Uuid(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("occupied", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pool_id"],
            ["resource_pool.id"],
            name="fk_resource_pool_resource_pool_id_resource_pool",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pool_id", "key", name="unique_resource_pool_resource_pool_id_key"
        ),
    )
    op.create_table(
        "resource_pool_subject_policy",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("component_id", sa.Uuid(), nullable=False),
        sa.Column("pool_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["stack_component.id"],
            name="fk_resource_pool_subject_policy_component_id_stack_component",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pool_id"],
            ["resource_pool.id"],
            name="fk_resource_pool_subject_policy_pool_id_resource_pool",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_resource_pool_subject_policy_user_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id", "pool_id", name="unique_component_id_pool_id"
        ),
    )
    with op.batch_alter_table(
        "resource_pool_subject_policy", schema=None
    ) as batch_op:
        batch_op.create_index(
            "ix_resource_pool_subject_policy_component_id_priority_pool_id",
            ["component_id", "priority", "pool_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_resource_pool_subject_policy_pool_id_component_id",
            ["pool_id", "component_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_resource_pool_subject_policy_pool_id_priority_component_id",
            ["pool_id", "priority", "component_id"],
            unique=False,
        )

    op.create_table(
        "resource_pool_subject_policy_resource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["resource_pool_subject_policy.id"],
            name="fk_pool_subject_policy_resource_policy_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_id",
            "key",
            name="unique_resource_pool_subject_policy_resource",
        ),
    )
    op.create_table(
        "resource_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("component_id", sa.Uuid(), nullable=True),
        sa.Column("step_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "preemption_initiated_by_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "status_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("preemptible", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["stack_component.id"],
            name="fk_resource_request_component_id_stack_component",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["preemption_initiated_by_id"],
            ["resource_request.id"],
            name="fk_resource_request_preemption_initiated_by_id_resource_request",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"],
            ["step_run.id"],
            name="fk_resource_request_step_run_id_step_run",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_resource_request_user_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "step_run_id", name="unique_resource_request_step_run_id"
        ),
    )
    with op.batch_alter_table("resource_request", schema=None) as batch_op:
        batch_op.create_index(
            "ix_resource_request_component_id_status_created_id",
            ["component_id", "status", "created", "id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_resource_request_step_run_id_status_id",
            ["step_run_id", "status", "id"],
            unique=False,
        )

    op.create_table(
        "resource_pool_allocation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("pool_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("allocated_at", sa.DateTime(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pool_id"],
            ["resource_pool.id"],
            name="fk_resource_pool_allocation_pool_id_resource_pool",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["resource_request.id"],
            name="fk_resource_pool_allocation_request_id_resource_request",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_id", name="unique_resource_pool_allocation_request_id"
        ),
    )
    with op.batch_alter_table(
        "resource_pool_allocation", schema=None
    ) as batch_op:
        batch_op.create_index(
            "ix_resource_pool_allocation_pool_id_released_at_allocated_at_req",
            ["pool_id", "released_at", "allocated_at", "request_id"],
            unique=False,
        )

    op.create_table(
        "resource_pool_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("pool_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("request_created", sa.DateTime(), nullable=False),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pool_id"],
            ["resource_pool.id"],
            name="fk_resource_pool_queue_pool_id_resource_pool",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["resource_request.id"],
            name="fk_resource_pool_queue_request_id_resource_request",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pool_id",
            "request_id",
            name="unique_resource_pool_queue_pool_id_request_id",
        ),
    )
    with op.batch_alter_table("resource_pool_queue", schema=None) as batch_op:
        batch_op.create_index(
            "ix_resource_pool_queue_pool_id_claim_expires_at_priority_request",
            [
                "pool_id",
                "claim_expires_at",
                "priority",
                "request_created",
                "request_id",
            ],
            unique=False,
        )
        batch_op.create_index(
            "ix_resource_pool_queue_pool_id_priority_request_created_request_",
            ["pool_id", "priority", "request_created", "request_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_resource_pool_queue_request_id", ["request_id"], unique=False
        )

    op.create_table(
        "resource_request_resource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["resource_request.id"],
            name="fk_resource_request_resource_request_id_resource_request",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_id",
            "key",
            name="unique_resource_request_resource_request_id_key",
        ),
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_table("resource_request_resource")
    with op.batch_alter_table("resource_pool_queue", schema=None) as batch_op:
        batch_op.drop_index("ix_resource_pool_queue_request_id")
        batch_op.drop_index(
            "ix_resource_pool_queue_pool_id_priority_request_created_request_"
        )
        batch_op.drop_index(
            "ix_resource_pool_queue_pool_id_claim_expires_at_priority_request"
        )

    op.drop_table("resource_pool_queue")
    with op.batch_alter_table(
        "resource_pool_allocation", schema=None
    ) as batch_op:
        batch_op.drop_index(
            "ix_resource_pool_allocation_pool_id_released_at_allocated_at_req"
        )

    op.drop_table("resource_pool_allocation")
    with op.batch_alter_table("resource_request", schema=None) as batch_op:
        batch_op.drop_index("ix_resource_request_step_run_id_status_id")
        batch_op.drop_index(
            "ix_resource_request_component_id_status_created_id"
        )

    op.drop_table("resource_request")
    op.drop_table("resource_pool_subject_policy_resource")
    with op.batch_alter_table(
        "resource_pool_subject_policy", schema=None
    ) as batch_op:
        batch_op.drop_index(
            "ix_resource_pool_subject_policy_pool_id_priority_component_id"
        )
        batch_op.drop_index(
            "ix_resource_pool_subject_policy_pool_id_component_id"
        )
        batch_op.drop_index(
            "ix_resource_pool_subject_policy_component_id_priority_pool_id"
        )

    op.drop_table("resource_pool_subject_policy")
    op.drop_table("resource_pool_resource")
    op.drop_table("resource_pool")
