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
from sqlalchemy.orm import load_only, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, col

from zenml.models import (
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolResponseBody,
    ResourcePoolResponseMetadata,
    ResourcePoolResponseResources,
    ResourcePoolUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.resource_pool_policy_schemas import (
    ResourcePoolSubjectPolicySchema,
)
from zenml.zen_stores.schemas.resource_request_schemas import (
    ResourceRequestSchema,
)
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class ResourcePoolQueueSchema(BaseSchema, table=True):
    """Resource pool queue schema."""

    __tablename__ = "resource_pool_queue"
    __table_args__ = (
        UniqueConstraint(
            "pool_id",
            "request_id",
            name="unique_resource_pool_queue_pool_id_request_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["request_id"],
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
        build_index(
            table_name=__tablename__,
            column_names=[
                "pool_id",
                "claim_expires_at",
                "priority",
                "request_created",
                "request_id",
            ],
        ),
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
    request: "ResourceRequestSchema" = Relationship()
    priority: int
    request_created: datetime = Field(default_factory=utc_now)
    claim_token: Optional[UUID] = Field(default=None, nullable=True)
    claim_expires_at: Optional[datetime] = Field(default=None, nullable=True)


class ResourcePoolAllocationSchema(BaseSchema, table=True):
    """Resource pool allocation schema."""

    __tablename__ = "resource_pool_allocation"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            name="unique_resource_pool_allocation_request_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=[
                "pool_id",
                "released_at",
                "allocated_at",
                "request_id",
            ],
        ),
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
    request: "ResourceRequestSchema" = Relationship()
    policy: Optional["ResourcePoolSubjectPolicySchema"] = Relationship(
        sa_relationship_kwargs={
            "secondary": "resource_request",
            "primaryjoin": (
                "ResourcePoolAllocationSchema.request_id == "
                "ResourceRequestSchema.id"
            ),
            "secondaryjoin": (
                "and_("
                "ResourcePoolSubjectPolicySchema.pool_id == "
                "ResourcePoolAllocationSchema.pool_id, "
                "ResourcePoolSubjectPolicySchema.component_id == "
                "ResourceRequestSchema.component_id"
                ")"
            ),
            "uselist": False,
            "viewonly": True,
        }
    )
    allocated_at: datetime = Field(default_factory=utc_now)
    released_at: Optional[datetime] = Field(default=None, nullable=True)

    @property
    def priority(self) -> Optional[int]:
        """Fetch the priority for this allocation.

        Returns:
            The matching policy priority, if a policy exists.
        """
        return self.policy.priority if self.policy else None


class ResourcePoolSchema(NamedSchema, table=True):
    """Resource pool schema."""

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
    queue_items: List["ResourcePoolQueueSchema"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": (
                "ResourcePoolSchema.id == ResourcePoolQueueSchema.pool_id"
            ),
            "viewonly": True,
        }
    )
    policies: List["ResourcePoolSubjectPolicySchema"] = Relationship(
        sa_relationship_kwargs={
            "order_by": desc(col(ResourcePoolSubjectPolicySchema.priority)),
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        }
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
        options = [
            selectinload(jl_arg(ResourcePoolSchema.resources)),
            selectinload(jl_arg(ResourcePoolSchema.queue_items)).options(
                load_only(jl_arg(ResourcePoolQueueSchema.request_id))
            ),
        ]

        if include_resources:
            options.extend(
                [
                    selectinload(jl_arg(ResourcePoolSchema.user)),
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
            queue_length=len(self.queue_items),
            capacity={r.key: r.total for r in self.resources},
            occupied_resources={r.key: r.occupied for r in self.resources},
        )

        metadata = None
        if include_metadata:
            metadata = ResourcePoolResponseMetadata(
                description=self.description,
            )

        resources = None
        if include_resources:
            resources = ResourcePoolResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return ResourcePoolResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )


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
