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
"""Add trigger actions [e4a1c7d9b203].

Revision ID: e4a1c7d9b203
Revises: 0.96.4
Create Date: 2026-09-03

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "e4a1c7d9b203"
down_revision = "0.96.4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the trigger action table."""
    op.create_table(
        "trigger_action",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("updated", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("entity", sa.VARCHAR(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.VARCHAR(length=50), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_trigger_action_project_id_project",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["trigger_id"],
            ["trigger.id"],
            name="fk_trigger_action_trigger_id_trigger",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trigger_id",
            "name",
            name="unique_trigger_action_name",
        ),
    )


def downgrade() -> None:
    """Remove the trigger action table."""
    op.drop_table("trigger_action")
