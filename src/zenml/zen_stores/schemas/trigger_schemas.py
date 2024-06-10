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
from typing import Any, List, Optional, cast
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml import TriggerExecutionResponseResources
from zenml.models import (
    Page,
    TriggerExecutionRequest,
    TriggerExecutionResponse,
    TriggerExecutionResponseBody,
    TriggerExecutionResponseMetadata,
    TriggerRequest,
    TriggerResponse,
    TriggerResponseBody,
    TriggerResponseMetadata,
    TriggerResponseResources,
    TriggerUpdate,
)
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.event_source_schemas import EventSourceSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import get_page_from_list
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
    user: Optional["UserSchema"] = Relationship(
        back_populates="triggers",
        sa_relationship_kwargs={"foreign_keys": "[TriggerSchema.user_id]"},
    )

    event_source_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=EventSourceSchema.__tablename__,
        source_column="event_source_id",
        target_column="id",
        ondelete="CASCADE",  # TODO: this should be set null and the trigger should be deactivated
        nullable=False,
    )
    event_source: "EventSourceSchema" = Relationship(back_populates="triggers")

    executions: List["TriggerExecutionSchema"] = Relationship(
        back_populates="trigger"
    )

    service_account_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="service_account_id",
        target_column="id",
        ondelete="CASCADE",  # TODO: this should be set null and the trigger should be deactivated
        nullable=False,
    )
    service_account: UserSchema = Relationship(
        back_populates="auth_triggers",
        sa_relationship_kwargs={
            "foreign_keys": "[TriggerSchema.service_account_id]"
        },
    )
    auth_window: int

    event_filter: bytes

    action: bytes
    action_flavor: str  # <- "builtin"
    action_subtype: str  # <- "PipelineRun"

    description: str = Field(sa_column=Column(TEXT, nullable=True))
    is_active: bool = Field(nullable=False)

    def update(self, trigger_update: "TriggerUpdate") -> "TriggerSchema":
        """Updates a trigger schema with a trigger update model.

        Args:
            trigger_update: `TriggerUpdate` to update the trigger with.

        Returns:
            The updated TriggerSchema.
        """
        for field, value in trigger_update.model_dump(
            exclude_unset=True,
            exclude_none=True,
        ).items():
            if field == "event_filter":
                self.event_filter = base64.b64encode(
                    json.dumps(
                        trigger_update.event_filter, default=pydantic_encoder
                    ).encode("utf-8")
                )
            elif field == "action":
                self.action = base64.b64encode(
                    json.dumps(
                        trigger_update.action, default=pydantic_encoder
                    ).encode("utf-8")
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

        Raises:
            ValueError: If `auth_window` is not set.
        """
        if request.auth_window is None:
            raise ValueError("auth_window must be set")
        return cls(
            name=request.name,
            workspace_id=request.workspace,
            user_id=request.user,
            action=base64.b64encode(
                json.dumps(request.action, default=pydantic_encoder).encode(
                    "utf-8"
                ),
            ),
            action_flavor=request.action_flavor,
            action_subtype=request.action_subtype,
            event_source_id=request.event_source_id,
            service_account_id=request.service_account_id,
            auth_window=request.auth_window,
            event_filter=base64.b64encode(
                json.dumps(
                    request.event_filter, default=pydantic_encoder
                ).encode("utf-8")
            ),
            description=request.description,
            is_active=True,  # Makes no sense for it to be created inactive
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "TriggerResponse":
        """Converts the schema to a model.

        Args:
            include_metadata: Flag deciding whether to include the output model(s)
                metadata fields in the response.
            include_resources: Flag deciding whether to include the output model(s)
                metadata fields in the response.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The converted model.
        """
        from zenml.models import TriggerExecutionResponse

        body = TriggerResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            action_flavor=self.action_flavor,
            action_subtype=self.action_subtype,
            event_source_flavor=self.event_source.flavor,
            is_active=self.is_active,
        )
        metadata = None
        if include_metadata:
            metadata = TriggerResponseMetadata(
                workspace=self.workspace.to_model(),
                event_filter=json.loads(
                    base64.b64decode(self.event_filter).decode()
                ),
                action=json.loads(base64.b64decode(self.action).decode()),
                description=self.description,
                auth_window=self.auth_window,
            )
        resources = None
        if include_resources:
            executions = cast(
                Page[TriggerExecutionResponse],
                get_page_from_list(
                    items_list=self.executions,
                    response_model=TriggerExecutionResponse,
                    include_resources=include_resources,
                    include_metadata=include_metadata,
                ),
            )
            resources = TriggerResponseResources(
                event_source=self.event_source.to_model(),
                service_account=self.service_account.to_model(),
                executions=executions,
            )
        return TriggerResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
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

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "TriggerExecutionResponse":
        """Converts the schema to a model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The converted model.
        """
        body = TriggerExecutionResponseBody(
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = TriggerExecutionResponseMetadata(
                event_metadata=json.loads(
                    base64.b64decode(self.event_metadata).decode()
                )
                if self.event_metadata
                else {},
            )
        resources = None
        if include_resources:
            resources = TriggerExecutionResponseResources(
                trigger=self.trigger.to_model(),
            )

        return TriggerExecutionResponse(
            id=self.id, body=body, metadata=metadata, resources=resources
        )
