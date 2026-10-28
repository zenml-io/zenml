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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Add a persisted pipeline run stop mode.

Revision ID: 8e15c17d2a40
Revises: 0.98.0
"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "8e15c17d2a40"
down_revision = "0.98.0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable stop intent without inferring historical stop modes."""
    with op.batch_alter_table("pipeline_run") as batch_op:
        batch_op.add_column(
            sa.Column(
                "stop_mode", sqlmodel.sql.sqltypes.AutoString(), nullable=True
            )
        )


def downgrade() -> None:
    """Remove the pipeline run stop mode."""
    with op.batch_alter_table("pipeline_run") as batch_op:
        batch_op.drop_column("stop_mode")
