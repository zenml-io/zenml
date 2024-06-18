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
"""SQL Model Implementations for event sources."""

import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, cast
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml import EventSourceResponseMetadata
from zenml.models import (
    EventSourceRequest,
    EventSourceResponse,
    EventSourceResponseBody,
    EventSourceResponseResources,
    EventSourceUpdate,
    Page,
)
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import get_page_from_list
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import TriggerSchema


class EventSourceSchema(NamedSchema, table=True):
    """SQL Model for tag."""

    __tablename__ = "event_source"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="event_sources")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="event_sources")

    triggers: List["TriggerSchema"] = Relationship(
        back_populates="event_source"
    )

    flavor: str = Field(nullable=False)
    plugin_subtype: str = Field(nullable=False)
    description: str = Field(sa_column=Column(TEXT, nullable=True))

    configuration: bytes
    is_active: bool = Field(nullable=False)

    @classmethod
    def from_request(cls, request: EventSourceRequest) -> "EventSourceSchema":
        """Convert an `EventSourceRequest` to an `EventSourceSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            workspace_id=request.workspace,
            user_id=request.user,
            flavor=request.flavor,
            plugin_subtype=request.plugin_subtype,
            name=request.name,
            description=request.description,
            configuration=base64.b64encode(
                json.dumps(
                    request.configuration,
                    sort_keys=False,
                    default=pydantic_encoder,
                ).encode("utf-8")
            ),
            is_active=True,  # Makes no sense to create an inactive event source
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> EventSourceResponse:
        """Convert an `EventSourceSchema` to an `EventSourceResponse`.

        Args:
            include_metadata: Flag deciding whether to include the output model(s)
                metadata fields in the response.
            include_resources: Flag deciding whether to include the output model(s)
                metadata fields in the response.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The created `EventSourceResponse`.
        """
        from zenml.models import TriggerResponse

        body = EventSourceResponseBody(
            created=self.created,
            updated=self.updated,
            user=self.user.to_model() if self.user else None,
            flavor=self.flavor,
            plugin_subtype=self.plugin_subtype,
            is_active=self.is_active,
        )
        resources = None
        if include_resources:
            triggers = cast(
                Page[TriggerResponse],
                get_page_from_list(
                    items_list=self.triggers,
                    response_model=TriggerResponse,
                    include_resources=include_resources,
                    include_metadata=include_metadata,
                ),
            )
            resources = EventSourceResponseResources(
                triggers=triggers,
            )
        metadata = None
        if include_metadata:
            metadata = EventSourceResponseMetadata(
                workspace=self.workspace.to_model(),
                description=self.description,
                configuration=json.loads(
                    base64.b64decode(self.configuration).decode()
                ),
            )
        return EventSourceResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(self, update: EventSourceUpdate) -> "EventSourceSchema":
        """Updates a `EventSourceSchema` from a `EventSourceUpdate`.

        Args:
            update: The `EventSourceUpdate` to update from.

        Returns:
            The updated `EventSourceSchema`.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "configuration":
                self.configuration = base64.b64encode(
                    json.dumps(
                        update.configuration, default=pydantic_encoder
                    ).encode("utf-8")
                )
            else:
                setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self
