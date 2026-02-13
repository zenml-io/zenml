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
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint, desc, exists
from sqlalchemy.orm import object_session, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, and_, col, select

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
from zenml.models.v2.core.resource_pool import (
    ResourcePoolAllocation,
    ResourcePoolQueueItem,
    ResourcePoolSubjectPolicyResponse,
)
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


# TODO: rename to ResourcePoolQueueSchema
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
    allocated_at: datetime = Field(default_factory=utc_now)
    released_at: Optional[datetime] = Field(default=None, nullable=True)

    @property
    def priority(self) -> int:
        """Fetch the priority for this allocation.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The priority for this allocation.
        """
        if session := object_session(self):
            return session.execute(
                select(ResourcePoolSubjectPolicySchema.priority)
                .where(
                    ResourcePoolSubjectPolicySchema.resource_pool_id
                    == self.pool_id
                )
                .where(ResourceRequestSchema.id == self.request_id)
                .where(
                    ResourcePoolSubjectPolicySchema.component_id
                    == ResourceRequestSchema.component_id
                )
                .limit(1)
            ).scalar_one()
        else:
            raise RuntimeError(
                "Missing DB session to fetch priority for allocation."
            )


class ResourcePoolSubjectPolicySchema(BaseSchema, table=True):
    """Resource pool subject policy schema."""

    __tablename__ = "resource_pool_subject_policy"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "resource_pool_id",
            name="unique_component_id_resource_pool_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["resource_pool_id", "priority", "component_id"],
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
    resources: List["ResourcePoolSubjectPolicyResourceSchema"] = Relationship(
        back_populates="policy",
        sa_relationship_kwargs={
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        },
    )


class ResourcePoolSubjectPolicyResourceSchema(BaseSchema, table=True):
    """Per-resource min/max share configuration for a pool subject policy."""

    __tablename__ = "resource_pool_subject_policy_resource"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "key",
            name="unique_resource_pool_subject_policy_resource",
        ),
    )
    policy_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourcePoolSubjectPolicySchema.__tablename__,
        source_column="policy_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        custom_constraint_name="fk_pool_subject_policy_resource_policy_id",
    )
    key: str
    reserved: int = Field(default=0, nullable=False)
    limit: Optional[int] = Field(default=None, nullable=True)

    policy: Optional["ResourcePoolSubjectPolicySchema"] = Relationship(
        back_populates="resources"
    )


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
    policies: List["ResourcePoolSubjectPolicySchema"] = Relationship(
        sa_relationship_kwargs={
            "order_by": desc(col(ResourcePoolSubjectPolicySchema.priority)),
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        }
    )

    # TODO: The order of this might not actually be the same as the order in
    # which requests will be allocated. To get that, we would have to consider
    # the free dedicated resources of each policy, which is a query that we only
    # run as part of the actual allocation process.
    queue_items: List["ResourcePoolQueueSchema"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": lambda: and_(
                col(ResourcePoolSchema.id)
                == col(ResourcePoolQueueSchema.pool_id),
                exists(
                    select(1).where(
                        col(ResourceRequestSchema.id)
                        == col(ResourcePoolQueueSchema.request_id),
                        col(ResourceRequestSchema.status)
                        == ResourceRequestStatus.PENDING.value,
                    )
                ),
            ),
            "order_by": (
                desc(col(ResourcePoolQueueSchema.priority)),
                ResourcePoolQueueSchema.request_created,
                ResourcePoolQueueSchema.request_id,
            ),
            "passive_deletes": True,
        },
    )
    allocations: List["ResourcePoolAllocationSchema"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": lambda: and_(
                col(ResourcePoolSchema.id)
                == col(ResourcePoolAllocationSchema.pool_id),
                col(ResourcePoolAllocationSchema.released_at).is_(None),
            ),
            "order_by": (
                col(ResourcePoolAllocationSchema.allocated_at),
                ResourcePoolAllocationSchema.request_id,
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

        if include_metadata:
            options.extend(
                [
                    selectinload(jl_arg(ResourcePoolSchema.resources)),
                ]
            )

        if include_resources:
            options.extend(
                [
                    selectinload(
                        jl_arg(ResourcePoolSchema.policies)
                    ).joinedload(
                        jl_arg(ResourcePoolSubjectPolicySchema.component)
                    ),
                    selectinload(
                        jl_arg(ResourcePoolSchema.queue_items)
                    ).joinedload(jl_arg(ResourcePoolQueueSchema.request)),
                    selectinload(
                        jl_arg(ResourcePoolSchema.allocations)
                    ).joinedload(jl_arg(ResourcePoolAllocationSchema.request)),
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

    def _get_borrowed_resources_per_allocation(
        self,
    ) -> Dict[UUID, Dict[str, int]]:
        """Compute borrowed resources for each active allocation.

        The computation is done per policy and in allocation order (oldest
        first): each allocation first consumes dedicated reserved resources of
        the policy and only the overflow is counted as borrowed.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            Mapping from request ID to borrowed resources for that allocation.
        """
        if not (session := object_session(self)):
            raise RuntimeError(
                "Missing DB session to compute borrowed resources."
            )

        policies = session.execute(
            select(ResourcePoolSubjectPolicySchema)
            .where(ResourcePoolSubjectPolicySchema.resource_pool_id == self.id)
            .options(
                selectinload(jl_arg(ResourcePoolSubjectPolicySchema.resources))
            )
        ).scalars()

        policy_id_by_component: Dict[UUID, UUID] = {}
        reserved_resources_by_policy: Dict[UUID, Dict[str, int]] = {}
        for policy in policies:
            policy_id_by_component[policy.component_id] = policy.id
            reserved_resources_by_policy[policy.id] = {
                resource.key: resource.reserved
                for resource in policy.resources
            }

        current_usage_by_policy: Dict[UUID, Dict[str, int]] = {}
        borrowed_by_allocation: Dict[UUID, Dict[str, int]] = {}

        for allocation in self.allocations:
            policy_id = policy_id_by_component.get(
                allocation.request.component_id
            )

            if policy_id is None:
                continue

            reserved_resources = reserved_resources_by_policy[policy_id]
            policy_usage = current_usage_by_policy.setdefault(policy_id, {})

            borrowed_resources: Dict[str, int] = {}
            requested_resources = {
                resource.key: resource.amount
                for resource in allocation.request.requested_resources
            }
            for resource_key, requested_amount in requested_resources.items():
                used_before = policy_usage.get(resource_key, 0)
                reserved_amount = reserved_resources.get(resource_key, 0)
                available_reserved = max(0, reserved_amount - used_before)
                borrowed_amount = max(0, requested_amount - available_reserved)

                if borrowed_amount:
                    borrowed_resources[resource_key] = borrowed_amount

                policy_usage[resource_key] = used_before + requested_amount

            borrowed_by_allocation[allocation.id] = borrowed_resources

        return borrowed_by_allocation

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
                ResourcePoolSubjectPolicyResponse(
                    **policy.component.to_model().model_dump(),
                    priority=policy.priority,
                    reserved={r.key: r.reserved for r in policy.resources},
                    limit={
                        r.key: r.limit
                        for r in policy.resources
                        if r.limit is not None
                    },
                )
                for policy in self.policies
            ]
            # TODO: We shouldn't include metadata/resources here.
            queued_requests = [
                ResourcePoolQueueItem(
                    request=i.request.to_model(
                        include_metadata=True, include_resources=True
                    ),
                    priority=i.priority,
                )
                for i in self.queue_items
            ]
            borrowed_resources = self._get_borrowed_resources_per_allocation()
            active_requests = [
                ResourcePoolAllocation(
                    request=a.request.to_model(
                        include_metadata=True, include_resources=True
                    ),
                    priority=a.priority,
                    allocated_at=a.allocated_at,
                    borrowed_resources=borrowed_resources.get(a.id, {}),
                )
                for a in self.allocations
            ]
            resources = ResourcePoolResponseResources(
                user=self.user.to_model() if self.user else None,
                policies=components,
                queued_requests=queued_requests,
                active_requests=active_requests,
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
    preemption_initiated_by_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=__tablename__,
        source_column="preemption_initiated_by_id",
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
    step_run: Optional["StepRunSchema"] = Relationship(
        back_populates="resource_request"
    )
    preemption_initiated_by: Optional["ResourceRequestSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[ResourceRequestSchema.preemption_initiated_by_id]",
            "remote_side": "ResourceRequestSchema.id",
        }
    )

    requested_resources: List["ResourceRequestResourceSchema"] = Relationship(
        back_populates="request",
        sa_relationship_kwargs={
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        },
    )
    status: str
    status_reason: Optional[str] = Field(default=None, nullable=True)

    @property
    def running_in_pool(self) -> Optional["ResourcePoolSchema"]:
        """Get the pool that the resource request is running in.

        Raises:
            RuntimeError: If no session for the schema exists.

        Returns:
            The pool that the resource request is running in.
        """
        if session := object_session(self):
            return session.execute(
                select(ResourcePoolSchema)
                .join(
                    ResourcePoolAllocationSchema,
                    col(ResourcePoolAllocationSchema.pool_id)
                    == ResourcePoolSchema.id,
                )
                .where(col(ResourcePoolAllocationSchema.request_id) == self.id)
                .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
                .limit(1)
            ).scalar_one_or_none()
        else:
            raise RuntimeError(
                "Missing DB session to fetch pool for resource request."
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

        if include_metadata:
            options.extend(
                [
                    selectinload(
                        jl_arg(ResourceRequestSchema.requested_resources)
                    ),
                ]
            )

        if include_resources:
            options.extend(
                [
                    selectinload(jl_arg(ResourceRequestSchema.component)),
                    selectinload(
                        jl_arg(ResourceRequestSchema.step_run)
                    ).joinedload(jl_arg(StepRunSchema.pipeline_run)),
                    selectinload(
                        jl_arg(ResourceRequestSchema.preemption_initiated_by)
                    ),
                    selectinload(jl_arg(ResourceRequestSchema.user)),
                ]
            )

        return options

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
            preemption_initiated_by_id=None,
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
            status_reason=self.status_reason,
        )

        metadata = None
        if include_metadata:
            metadata = ResourceRequestResponseMetadata(
                requested_resources={
                    r.key: r.amount for r in self.requested_resources
                },
            )

        resources = None
        if include_resources:
            # TODO: Combined with the `include_resources=True` for all requests
            # of a pool response, this creates quite a bit of overhead.
            running_in_pool = (
                self.running_in_pool.to_model()
                if self.running_in_pool
                else None
            )
            resources = ResourceRequestResponseResources(
                user=self.user.to_model() if self.user else None,
                component=self.component.to_model(),
                step_run=self.step_run.to_model() if self.step_run else None,
                pipeline_run=self.step_run.pipeline_run.to_model()
                if self.step_run
                else None,
                preemption_initiated_by_id=self.preemption_initiated_by.to_model()
                if self.preemption_initiated_by
                else None,
                running_in_pool=running_in_pool,
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
