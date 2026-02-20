# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""SQL Model Implementations for Triggers Associations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field


class TriggerSnapshotSchema(SQLModel, table=True):
    """Association table linking triggers to pipeline snapshots.

    - Enforces uniqueness per (trigger_id, snapshot_id)
    - Cascades deletes from either parent row (DB-level ON DELETE CASCADE)
    """

    __tablename__ = "trigger_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "trigger_id",
            "snapshot_id",
            name="unique_trigger_snapshot_link",
        ),
    )

    trigger_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="trigger",
        source_column="trigger_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    snapshot_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_snapshot",
        source_column="snapshot_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    created_at: datetime = Field(default_factory=utc_now)


class TriggerExecutionSchema(SQLModel, table=True):
    """Association table linking triggers to pipeline snapshots.

    - Enforces uniqueness per (trigger_id, snapshot_id)
    - Cascades deletes from either parent row (DB-level ON DELETE CASCADE)
    """

    __tablename__ = "trigger_execution"
    __table_args__ = (
        UniqueConstraint(
            "trigger_id",
            "pipeline_run_id",
            name="unique_trigger_execution",
        ),
    )

    trigger_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="trigger",
        source_column="trigger_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    pipeline_run_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_run",
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )

    created_at: datetime = Field(default_factory=utc_now)

    # TriggerExecution -> 1 PipelineRun
    pipeline_run: "PipelineRunSchema" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select",
        },
    )
