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
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TEXT, VARCHAR, Column, String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models import TriggerActionRequest, TriggerActionResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.models import TriggerSnapshotDispatchState
    from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema


class TriggerActionSchema(NamedSchema, table=True):
    """Action attached to a trigger."""

    __tablename__ = "trigger_action"
    __table_args__ = (
        UniqueConstraint(
            "trigger_id",
            "name",
            name="unique_trigger_action_name",
        ),
    )

    entity: str = Field(sa_column=Column(VARCHAR(50), nullable=False))
    entity_id: UUID = Field(nullable=False)
    operation: str = Field(sa_column=Column(VARCHAR(50), nullable=False))

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="project",
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    trigger_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="trigger",
        source_column="trigger_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    trigger: "TriggerSchema" = Relationship(back_populates="actions")

    @classmethod
    def from_request(
        cls,
        request: TriggerActionRequest,
        trigger_id: UUID,
        project_id: UUID,
    ) -> "TriggerActionSchema":
        """Create a schema from an attachment request.

        Args:
            request: The trigger action request.
            trigger_id: The target trigger ID.
            project_id: The trigger project ID.

        Returns:
            The trigger action schema.
        """
        return cls(
            name=request.name,
            entity=request.entity.value,
            entity_id=request.entity_id,
            operation=request.operation.value,
            project_id=project_id,
            trigger_id=trigger_id,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: object,
    ) -> TriggerActionResponse:
        """Convert the schema to a response model.

        Args:
            include_metadata: Unused compatibility flag.
            include_resources: Unused compatibility flag.
            **kwargs: Unused compatibility keyword arguments.

        Returns:
            The trigger action response.
        """
        return TriggerActionResponse.model_validate(self, from_attributes=True)


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

    dispatch_state: str | None = Field(
        sa_column=Column(
            String(length=TEXT_FIELD_MAX_LENGTH).with_variant(TEXT, "mysql"),
            nullable=True,
            default=None,
        ),
    )

    @property
    def parsed_dispatch_state(self) -> "TriggerSnapshotDispatchState | None":
        """Parse persisted dispatch-state JSON into the typed model.

        Returns:
            Parsed trigger dispatch state or ``None`` if missing/invalid.
        """
        if not self.dispatch_state:
            return None
        try:
            from zenml.models import TriggerSnapshotDispatchState

            return TriggerSnapshotDispatchState.model_validate_json(
                self.dispatch_state
            )
        except Exception:
            return None


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

    info: str | None = Field(
        sa_column=Column(
            String(length=TEXT_FIELD_MAX_LENGTH).with_variant(TEXT, "mysql"),
            nullable=True,
            default=None,
        ),
        description="JSON object - extra info on trigger execution.",
    )
