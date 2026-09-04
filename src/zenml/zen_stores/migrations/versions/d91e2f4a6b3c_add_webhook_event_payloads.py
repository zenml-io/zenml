#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Add retained webhook event payloads [d91e2f4a6b3c].

Revision ID: d91e2f4a6b3c
Revises: 7c0d9e4a1b2f
Create Date: 2026-09-04

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import LONGBLOB

revision = "d91e2f4a6b3c"
down_revision = "7c0d9e4a1b2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the retained webhook event payload table."""
    op.create_table(
        "webhook_event_payload",
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.String(length=255), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "payload",
            LONGBLOB
            if op.get_bind().dialect.name == "mysql"
            else sa.LargeBinary(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["webhook_id"],
            ["webhook.id"],
            name="fk_webhook_event_payload_webhook_id_webhook",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("webhook_id", "delivery_id"),
    )
    op.create_index(
        "ix_webhook_event_payload_expires_at",
        "webhook_event_payload",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the retained webhook event payload table."""
    op.drop_index(
        "ix_webhook_event_payload_expires_at",
        table_name="webhook_event_payload",
    )
    op.drop_table("webhook_event_payload")
