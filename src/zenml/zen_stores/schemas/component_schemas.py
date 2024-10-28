#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""SQL Model Implementations for Stack Components."""

import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlmodel import Relationship

from zenml.enums import StackComponentType
from zenml.models import (
    ComponentRequest,
    ComponentResponse,
    ComponentResponseBody,
    ComponentResponseMetadata,
    ComponentResponseResources,
    ComponentUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.service_connector_schemas import (
    ServiceConnectorSchema,
)
from zenml.zen_stores.schemas.stack_schemas import StackCompositionSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.flavor_schemas import FlavorSchema
    from zenml.zen_stores.schemas.logs_schemas import LogsSchema
    from zenml.zen_stores.schemas.run_metadata_schemas import RunMetadataSchema
    from zenml.zen_stores.schemas.schedule_schema import ScheduleSchema
    from zenml.zen_stores.schemas.stack_schemas import StackSchema


class StackComponentSchema(NamedSchema, table=True):
    """SQL Model for stack components."""

    __tablename__ = "stack_component"

    type: str
    flavor: str
    configuration: bytes
    labels: Optional[bytes]
    component_spec_path: Optional[str]

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="components")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="components")

    stacks: List["StackSchema"] = Relationship(
        back_populates="components", link_model=StackCompositionSchema
    )
    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="orchestrator",
    )

    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="stack_component",
    )
    flavor_schema: Optional["FlavorSchema"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "and_(foreign(StackComponentSchema.flavor) == FlavorSchema.name, foreign(StackComponentSchema.type) == FlavorSchema.type)",
            "lazy": "joined",
            "uselist": False,
        },
    )

    run_or_step_logs: List["LogsSchema"] = Relationship(
        back_populates="artifact_store",
        sa_relationship_kwargs={"cascade": "delete", "uselist": True},
    )

    connector_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ServiceConnectorSchema.__tablename__,
        source_column="connector_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    connector: Optional["ServiceConnectorSchema"] = Relationship(
        back_populates="components"
    )

    connector_resource_id: Optional[str]

    @classmethod
    def from_request(
        cls,
        request: "ComponentRequest",
        service_connector: Optional[ServiceConnectorSchema] = None,
    ) -> "StackComponentSchema":
        """Create a component schema from a request.

        Args:
            request: The request from which to create the component.
            service_connector: Optional service connector to link to the
                component.

        Returns:
            The component schema.
        """
        return cls(
            name=request.name,
            workspace_id=request.workspace,
            user_id=request.user,
            component_spec_path=request.component_spec_path,
            type=request.type,
            flavor=request.flavor,
            configuration=base64.b64encode(
                json.dumps(request.configuration).encode("utf-8")
            ),
            labels=base64.b64encode(
                json.dumps(request.labels).encode("utf-8")
            ),
            connector=service_connector,
            connector_resource_id=request.connector_resource_id,
        )

    def update(
        self, component_update: "ComponentUpdate"
    ) -> "StackComponentSchema":
        """Updates a `StackComponentSchema` from a `ComponentUpdate`.

        Args:
            component_update: The `ComponentUpdate` to update from.

        Returns:
            The updated `StackComponentSchema`.
        """
        for field, value in component_update.model_dump(
            exclude_unset=True, exclude={"workspace", "user", "connector"}
        ).items():
            if field == "configuration":
                self.configuration = base64.b64encode(
                    json.dumps(component_update.configuration).encode("utf-8")
                )
            elif field == "labels":
                self.labels = base64.b64encode(
                    json.dumps(component_update.labels).encode("utf-8")
                )
            elif field == "type":
                component_type = component_update.type

                if component_type is not None:
                    self.type = component_type
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "ComponentResponse":
        """Creates a `ComponentModel` from an instance of a `StackComponentSchema`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Raises:
            RuntimeError: If the flavor for the component is missing in the DB.

        Returns:
            A `ComponentModel`
        """
        body = ComponentResponseBody(
            type=StackComponentType(self.type),
            flavor_name=self.flavor,
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
            logo_url=self.flavor_schema.logo_url
            if self.flavor_schema
            else None,
            integration=self.flavor_schema.integration
            if self.flavor_schema
            else None,
        )
        metadata = None
        if include_metadata:
            metadata = ComponentResponseMetadata(
                workspace=self.workspace.to_model(),
                configuration=json.loads(
                    base64.b64decode(self.configuration).decode()
                ),
                labels=json.loads(base64.b64decode(self.labels).decode())
                if self.labels
                else None,
                component_spec_path=self.component_spec_path,
                connector_resource_id=self.connector_resource_id,
                connector=self.connector.to_model()
                if self.connector
                else None,
            )
        resources = None
        if include_resources:
            if not self.flavor_schema:
                raise RuntimeError(
                    f"Missing flavor {self.flavor} for component {self.name}."
                )

            resources = ComponentResponseResources(
                flavor=self.flavor_schema.to_model()
            )
        return ComponentResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
