#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""SQL Model Implementations for Triggers."""
import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.models import (
    TriggerExecutionRequest,
    TriggerExecutionResponse,
    TriggerExecutionResponseBody,
    TriggerExecutionResponseMetadata,
    TriggerRequest,
    TriggerResponse,
    TriggerResponseBody,
    TriggerResponseMetadata,
    TriggerUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.event_source_schemas import EventSourceSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.action_resource_schemas import (
        ActionResourceSchema,
    )


class ActionResourceCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    __tablename__ = "action_resource_composition"

    trigger_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="trigger",
        source_column="trigger_id",
        target_column="id",
        ondelete="CASCADE",  # Figure this out
        nullable=False,
        primary_key=True,
    )
    action_resource_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="action_resource",
        source_column="action_resource_id",
        target_column="id",
        ondelete="CASCADE",  # Figure this out
        nullable=False,
        primary_key=True,
    )


class TriggerSchema(NamedSchema, table=True):
    """SQL Model for triggers."""

    __tablename__ = "trigger"

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="triggers")

    event_source_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=EventSourceSchema.__tablename__,
        source_column="event_source_id",
        target_column="id",
        ondelete="CASCADE",  # TODO: this should be set null and the trigger should be deactivated
        nullable=False,
    )
    event_source: Optional["EventSourceSchema"] = Relationship(
        back_populates="triggers"
    )

    executions: List["TriggerExecutionSchema"] = Relationship(
        back_populates="trigger"
    )

    event_filter: bytes

    action: bytes
    action_flavor: str  # <- "builtin"
    action_subtype: str  # <- "PipelineRun"
    # resource_id: Optional[UUID]  # <- deployment_id
    resources: List["ActionResourceSchema"] = Relationship(
        back_populates="triggers",
        link_model=ActionResourceCompositionSchema,
    )

    description: str = Field(sa_column=Column(TEXT, nullable=True))
    is_active: bool = Field(nullable=False)

    def update(self, trigger_update: "TriggerUpdate") -> "TriggerSchema":
        """Updates a trigger schema with a trigger update model.

        Args:
            trigger_update: `TriggerUpdate` to update the trigger with.

        Returns:
            The updated TriggerSchema.
        """
        for field, value in trigger_update.dict(
            exclude_unset=True,
            exclude_none=True,
        ).items():
            if field == "event_filter":
                self.event_filter = base64.b64encode(
                    json.dumps(trigger_update.event_filter).encode("utf-8")
                )
            elif field == "action":
                self.action = base64.b64encode(
                    json.dumps(trigger_update.action).encode("utf-8")
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    @classmethod
    def from_request(cls, request: "TriggerRequest") -> "TriggerSchema":
        """Convert a `TriggerRequest` to a `TriggerSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            user_id=request.user,
            action=base64.b64encode(
                json.dumps(request.action).encode("utf-8")
            ),
            action_flavor=request.action_flavor,
            action_subtype=request.action_subtype,
            event_source_id=request.event_source_id,
            event_filter=base64.b64encode(
                json.dumps(request.event_filter).encode("utf-8")
            ),
            description=request.description,
            is_active=True,  # Makes no sense for it to be created inactive
        )

    def to_model(self, hydrate: bool = False) -> "TriggerResponse":
        """Converts the schema to a model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted model.
        """
        body = TriggerResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            action_flavor=self.action_flavor,
            action_subtype=self.action_subtype,
            # TODO: make event_source mandatory in the schema and ensure
            # triggers are deprovisioned and deleted before the event source is
            # deleted, or make it optional in the model
            event_source_flavor=self.event_source.flavor,
            is_active=self.is_active,
        )
        metadata = None
        if hydrate:
            metadata = TriggerResponseMetadata(
                event_filter=json.loads(
                    base64.b64decode(self.event_filter).decode()
                ),
                action=json.loads(base64.b64decode(self.action).decode()),
                description=self.description,
                # TODO: make event_source mandatory in the schema and ensure
                # triggers are deprovisioned and deleted before the event source is
                # deleted, or make it optional in the model
                event_source=self.event_source.to_model(),
            )

        return TriggerResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )


class TriggerExecutionSchema(BaseSchema, table=True):
    """SQL Model for trigger executions."""

    __tablename__ = "trigger_execution"

    trigger_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=TriggerSchema.__tablename__,
        source_column="trigger_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    trigger: TriggerSchema = Relationship(back_populates="executions")

    event_metadata: Optional[bytes] = None

    @classmethod
    def from_request(
        cls, request: "TriggerExecutionRequest"
    ) -> "TriggerExecutionSchema":
        """Convert a `TriggerExecutionRequest` to a `TriggerExecutionSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            trigger_id=request.trigger,
            event_metadata=base64.b64encode(
                json.dumps(request.event_metadata).encode("utf-8")
            ),
        )

    def to_model(self, hydrate: bool = False) -> "TriggerExecutionResponse":
        """Converts the schema to a model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted model.
        """
        body = TriggerExecutionResponseBody(
            trigger=self.trigger.to_model(),
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if hydrate:
            metadata = TriggerExecutionResponseMetadata(
                event_metadata=json.loads(
                    base64.b64decode(self.event_metadata).decode()
                )
                if self.event_metadata
                else {},
            )

        return TriggerExecutionResponse(
            id=self.id,
            body=body,
            metadata=metadata,
        )
