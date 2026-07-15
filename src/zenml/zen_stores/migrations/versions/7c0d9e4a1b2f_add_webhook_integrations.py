#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Add webhook integrations [7c0d9e4a1b2f].

Revision ID: 7c0d9e4a1b2f
Revises: b6f2a8d9c3e1
Create Date: 2026-07-07

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "7c0d9e4a1b2f"
down_revision = "b6f2a8d9c3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the webhook integration table."""
    op.create_table(
        "webhook_integration",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("secret_id", sa.Uuid(), nullable=False),
        sa.Column(
            "webhook_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "stats",
            sa.TEXT(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_webhook_integration_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_webhook_integration_user_id_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["secret_id"],
            ["secret.id"],
            name="fk_webhook_integration_secret_id_secret",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "name",
            name="unique_webhook_integration_name_in_project",
        ),
    )
    op.create_index(
        "ix_webhook_integration_webhook_type",
        "webhook_integration",
        ["webhook_type"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the webhook integration table."""
    op.drop_index(
        "ix_webhook_integration_webhook_type",
        table_name="webhook_integration",
    )
    op.drop_table("webhook_integration")
