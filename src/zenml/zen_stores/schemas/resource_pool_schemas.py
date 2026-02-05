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

from datetime import datetime
from typing import Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, col

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
from zenml.models.v2.core.resource_pool import ResourcePoolComponentResponse
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class ResourcePoolRequestQueueSchema(BaseSchema, table=True):
    """Resource pool request queue schema."""

    __tablename__ = "resource_pool_request_queue"
    __table_args__ = (
        UniqueConstraint(
            "pool_id",
            "request_id",
            name="unique_resource_pool_request_queue_pool_id_request_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=[
                "pool_id",
                "priority",
                "request_created",
                "request_id",
            ],
        ),
        build_index(table_name=__tablename__, column_names=["request_id"]),
    )

    pool_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="resource_pool",
        source_column="pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    request_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="resource_request",
        source_column="request_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    priority: int
    request_created: datetime = Field(default_factory=utc_now)


class ResourcePoolAssignmentSchema(BaseSchema, table=True):
    """Resource pool assignment schema."""

    __tablename__ = "resource_pool_assignment"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "resource_pool_id",
            name="unique_component_id_resource_pool_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["component_id", "priority", "resource_pool_id"],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["resource_pool_id", "component_id"],
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
    component: "StackComponentSchema" = Relationship()
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
    resources: List["ResourcePoolResourceSchema"] = Relationship(
        back_populates="pool",
        sa_relationship_kwargs={
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        },
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
    assigned_components: List["ResourcePoolAssignmentSchema"] = Relationship(
        sa_relationship_kwargs={
            "order_by": desc(col(ResourcePoolAssignmentSchema.priority)),
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        }
    )

    queued_requests: List["ResourceRequestSchema"] = Relationship(
        link_model=ResourcePoolRequestQueueSchema,
        sa_relationship_kwargs={
            "order_by": (
                desc(col(ResourcePoolRequestQueueSchema.priority)),
                ResourcePoolRequestQueueSchema.request_created,
                ResourcePoolRequestQueueSchema.request_id,
            ),
            "passive_deletes": True,
        },
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
                capacity={r.key: r.total for r in self.resources},
                occupied_resources={r.key: r.occupied for r in self.resources},
            )

        resources = None
        if include_resources:
            components = [
                ResourcePoolComponentResponse(
                    priority=a.priority,
                    **a.component.to_model().model_dump(),
                )
                for a in self.assigned_components
            ]
            resources = ResourcePoolResponseResources(
                user=self.user.to_model() if self.user else None,
                components=components,
                # TODO: include more info here
                queued_requests=[r.to_model() for r in self.queued_requests],
                # TODO: maybe include current active requests as well?
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
    __table_args__ = (
        build_index(
            table_name=__tablename__,
            column_names=["component_id", "status", "created", "id"],
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
    user: Optional["UserSchema"] = Relationship()
    component: "StackComponentSchema" = Relationship()
    step_run: Optional["StepRunSchema"] = Relationship()

    requested_resources: List["ResourceRequestResourceSchema"] = Relationship(
        back_populates="request",
    )
    status: str
    status_reason: Optional[str] = Field(default=None, nullable=True)

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
                status_reason=self.status_reason,
                requested_resources={
                    r.key: r.amount for r in self.requested_resources
                },
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


class ResourceRequestResourceSchema(BaseSchema, table=True):
    """Resource request resource schema."""

    __tablename__ = "resource_request_resource"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            "key",
            name="unique_resource_request_resource_request_id_key",
        ),
    )

    request_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourceRequestSchema.__tablename__,
        source_column="request_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    request: "ResourceRequestSchema" = Relationship(
        back_populates="requested_resources"
    )
    key: str
    amount: int


class ResourcePoolResourceSchema(BaseSchema, table=True):
    """Resource pool resource schema."""

    __tablename__ = "resource_pool_resource"
    __table_args__ = (
        UniqueConstraint(
            "pool_id",
            "key",
            name="unique_resource_pool_resource_pool_id_key",
        ),
    )

    pool_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourcePoolSchema.__tablename__,
        source_column="pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    pool: "ResourcePoolSchema" = Relationship(back_populates="resources")
    key: str
    total: int
    occupied: int = 0


class ResourcePoolAllocationSchema(BaseSchema, table=True):
    """Resource pool allocation schema."""

    __tablename__ = "resource_pool_allocation"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            name="unique_resource_pool_allocation_request_id",
        ),
        build_index(
            table_name=__tablename__, column_names=["pool_id", "released_at"]
        ),
    )

    pool_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourcePoolSchema.__tablename__,
        source_column="pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    request_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourceRequestSchema.__tablename__,
        source_column="request_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    allocated_at: datetime = Field(default_factory=utc_now)
    released_at: Optional[datetime] = Field(default=None, nullable=True)
