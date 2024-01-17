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
"""SQL Model Implementations for Action Plans."""
import json
from datetime import datetime
from typing import List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field
from pydantic.json import pydantic_encoder
from sqlalchemy import TEXT, Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Relationship

from zenml import TriggerResponseMetadata
from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    EventFilterRequest,
    EventFilterResponse,
    EventFilterResponseBody,
    EventFilterUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.event_source_schemas import EventSourceSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema


class EventFilterSchema(BaseSchema, table=True):
    """SQL Model for tag."""

    __tablename__ = "event_filter"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="triggers")
    event_source_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=EventSourceSchema.__tablename__,
        source_column="event_source_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    event_source: "WorkspaceSchema" = Relationship(back_populates="triggers")

    flavor: str = Field(nullable=False)

    configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    triggers: List["TriggerSchema"] = Relationship(back_populates="event_filter")
    description: str = Field(sa_column=Column(TEXT, nullable=True))

    @classmethod
    def from_request(cls, request: EventFilterRequest) -> "EventFilterSchema":
        """Convert an `EventFilterRequest` to an `EventFilterSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        # TODO: complete this
        return cls(
            flavor=request.flavor,
            configuration=json.dumps(
                request.configuration,
                sort_keys=False,
                default=pydantic_encoder,
            ),
        )

    def to_model(self, hydrate: bool = False) -> EventFilterResponse:
        """Convert an `EventFilterSchema` to an `EventFilterResponse`.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The created `TagResponse`.
        """
        body = EventFilterResponseBody(
            created=self.created,
            updated=self.updated,
            description=self.description
        )
        metadata = None
        if hydrate:
            metadata = TriggerResponseMetadata(
                workspace=self.workspace.to_model(),
                triggers=[t.to_model() for t in self.triggers],
            )

        return EventFilterResponse(
            id=self.id,
            body=body,
            metadata=metadata
        )

    def update(self, update: EventFilterUpdate) -> "EventFilterSchema":
        """Updates a `EventFilterSchema` from a `EventFilterUpdate`.

        Args:
            update: The `EventFilterUpdate` to update from.

        Returns:
            The updated `TagSchema`.
        """
        for field, value in update.dict(exclude_unset=True).items():
            setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self