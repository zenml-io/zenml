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
"""Resource Pool schemas."""

import base64
import json
from typing import Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.enums import ResourceRequestStatus
from zenml.models import (
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolResponseBody,
    ResourcePoolResponseMetadata,
    ResourcePoolResponseResources,
    ResourcePoolUpdate,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
    ResourceRequestUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class ResourcePoolAssignmentSchema(BaseSchema, table=True):
    """Resource pool assignment schema."""

    __tablename__ = "resource_pool_assignment"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "resource_pool_id",
            name="unique_component_id_resource_pool_id",
        ),
    )

    component_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    resource_pool_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="resource_pool",
        source_column="resource_pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )

    priority: int


class ResourcePoolSchema(NamedSchema, table=True):
    """SQL Model for resource pools."""

    __tablename__ = "resource_pool"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique_resource_pool_name",
        ),
    )

    description: Optional[str] = Field(default=None)
    total_resources: bytes = Field(title="The resources of the resource pool.")
    occupied_resources: bytes = Field(
        title="The occupied resources of the resource pool."
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship()
    components: List["StackComponentSchema"] = Relationship(
        # back_populates="resource_pools",
        link_model=ResourcePoolAssignmentSchema,
    )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether metadata will be included when converting
                the schema to a model.
            include_resources: Whether resources will be included when
                converting the schema to a model.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A list of query options.
        """
        options = []

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(ResourcePoolSchema.user)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls,
        request: "ResourcePoolRequest",
    ) -> "ResourcePoolSchema":
        """Create a resource pool schema from a request.

        Args:
            request: The request from which to create the resource pool.

        Returns:
            The resource pool schema.
        """
        return cls(
            name=request.name,
            user_id=request.user,
            description=request.description,
            total_resources=base64.b64encode(
                json.dumps(request.total_resources).encode("utf-8")
            ),
            occupied_resources=base64.b64encode(
                json.dumps({}).encode("utf-8")
            ),
        )

    def update(
        self, resource_pool_update: "ResourcePoolUpdate"
    ) -> "ResourcePoolSchema":
        """Updates a `ResourcePoolSchema` from a `ResourcePoolUpdate`.

        Args:
            resource_pool_update: The `ResourcePoolUpdate` to update from.

        Returns:
            The updated `ResourcePoolSchema`.
        """
        if resource_pool_update.description:
            self.description = resource_pool_update.description

        if resource_pool_update.total_resources:
            self.total_resources = base64.b64encode(
                json.dumps(resource_pool_update.total_resources).encode(
                    "utf-8"
                )
            )

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "ResourcePoolResponse":
        """Creates a `ResourcePoolResponse` from a `ResourcePoolSchema`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A `ResourcePoolResponse`
        """
        body = ResourcePoolResponseBody(
            created=self.created,
            updated=self.updated,
            user_id=self.user_id,
        )

        metadata = None
        if include_metadata:
            metadata = ResourcePoolResponseMetadata(
                description=self.description,
                total_resources=json.loads(
                    base64.b64decode(self.total_resources).decode()
                ),
                occupied_resources=json.loads(
                    base64.b64decode(self.occupied_resources).decode()
                ),
            )

        resources = None
        if include_resources:
            resources = ResourcePoolResponseResources(
                user=self.user.to_model() if self.user else None,
                components=[c.to_model() for c in self.components],
            )

        return ResourcePoolResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )


class ResourceRequestSchema(BaseSchema, table=True):
    """Resource request schema."""

    __tablename__ = "resource_request"

    component_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    occupied_pool_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ResourcePoolSchema.__tablename__,
        source_column="occupied_pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    occupied_pool: Optional["ResourcePoolSchema"] = Relationship()
    user: Optional["UserSchema"] = Relationship()
    component: "StackComponentSchema" = Relationship()
    step_run: Optional["StepRunSchema"] = Relationship()

    requested_resources: bytes
    status: str

    @classmethod
    def from_request(
        cls,
        request: "ResourceRequestRequest",
    ) -> "ResourceRequestSchema":
        """Create a resource request schema from a request.

        Args:
            request: The request from which to create the resource request.

        Returns:
            The resource request schema.
        """
        return cls(
            user_id=request.user,
            component_id=request.component_id,
            step_run_id=request.step_run_id,
            requested_resources=base64.b64encode(
                json.dumps(request.requested_resources).encode("utf-8")
            ),
            status=ResourceRequestStatus.PENDING.value,
        )

    def update(
        self, resource_request_update: "ResourceRequestUpdate"
    ) -> "ResourceRequestSchema":
        """Updates a `ResourceRequestSchema` from a `ResourceRequestUpdate`.

        Args:
            resource_request_update: The `ResourceRequestUpdate` to update from.

        Returns:
            The updated `ResourceRequestSchema`.
        """
        if resource_request_update.step_run_id:
            self.step_run_id = resource_request_update.step_run_id

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "ResourceRequestResponse":
        """Creates a `ResourceRequestResponse` from a `ResourceRequestSchema`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A `ResourceRequestResponse`
        """
        body = ResourceRequestResponseBody(
            created=self.created,
            updated=self.updated,
            user_id=self.user_id,
            status=ResourceRequestStatus(self.status),
        )

        metadata = None
        if include_metadata:
            metadata = ResourceRequestResponseMetadata(
                requested_resources=json.loads(
                    base64.b64decode(self.requested_resources).decode()
                ),
            )

        resources = None
        if include_resources:
            resources = ResourceRequestResponseResources(
                user=self.user.to_model() if self.user else None,
                component=self.component.to_model(),
                step_run=self.step_run.to_model() if self.step_run else None,
            )

        return ResourceRequestResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )
