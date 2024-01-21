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
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.v2.core.trigger import (
    TriggerRequest,
    TriggerResponse,
    TriggerResponseBody,
    TriggerResponseMetadata,
    TriggerUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class TriggerSchema(NamedSchema, table=True):
    """SQL Model for triggers."""

    __tablename__ = "trigger"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="triggers")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="triggers")

    event_filter: bytes
    event_flavor: str  # TODO: Use an Enum

    action_plan: bytes
    action_flavor: str  # TODO: Use an Enum

    description: str = Field(sa_column=Column(TEXT, nullable=True))

    def update(self, trigger_update: "TriggerUpdate") -> "TriggerSchema":
        """Updates a trigger schema with a trigger update model.

        Args:
            trigger_update: `TriggerUpdate` to update the trigger with.

        Returns:
            The updated TriggerSchema.
        """
        for field, value in trigger_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "event_filter":
                self.event_filter = base64.b64encode(
                    json.dumps(trigger_update.event_filter).encode("utf-8")
                )
                self.event_flavor = trigger_update.event_filter.get("flavor")
            elif field == "action_plan":
                self.action_plan = base64.b64encode(
                    json.dumps(trigger_update.action_plan).encode("utf-8")
                )
                self.action_flavor = trigger_update.action_plan.get("flavor")

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
            workspace_id=request.workspace,
            user_id=request.user,
            action_plan=base64.b64encode(
                    json.dumps(request.action_plan).encode("utf-8")
                ),
            action_flavor=request.action_plan.get("flavor"),
            event_filter=base64.b64encode(
                    json.dumps(request.event_filter).encode("utf-8")
                ),
            event_flavor=request.event_filter.get("flavor"),
            description=request.description,
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
            description=self.description,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if hydrate:
            metadata = TriggerResponseMetadata(
                workspace=self.workspace.to_model(),
                event_filter=json.loads(
                    base64.b64decode(self.event_filter).decode()
                ),
                action_plan=json.loads(
                    base64.b64decode(self.action_plan).decode()
                ),
            )

        return TriggerResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )
