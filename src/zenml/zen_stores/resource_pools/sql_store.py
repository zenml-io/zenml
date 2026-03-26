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
"""SQL Zen Store implementation."""

from zenml.zen_stores.resource_pools.store_interface import (
    ResourcePoolsStoreInterface,
)

try:
    import sqlalchemy  # noqa
except ImportError:
    raise ImportError(
        "It seems like you've installed the `zenml` package without the "
        "`local` extra, but are trying to use ZenML with a local database.\n"
        "* If you want to use ZenML in a local setup, please install "
        "`zenml[local]` instead, e.g. using `pip install 'zenml[local]'`\n"
        "* If you want to connect to a server, run `zenml login`"
    ) from None

from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)
from uuid import UUID, uuid4

from sqlalchemy import exists, func, update
from sqlalchemy.exc import (
    IntegrityError,
)
from sqlalchemy.orm import (
    selectinload,
)

# Important to note: The select function of SQLModel works slightly differently
# from the select function of sqlalchemy. If you input only one entity on the
# select function of SQLModel, it automatically maps it to a SelectOfScalar.
# As a result, it will not return a tuple as a result, but the first entity in
# the tuple. While this is convenient in most cases, in unique cases like using
# the "add_columns" functionality, one might encounter unexpected results.
from sqlmodel import (
    and_,
    case,
    col,
    delete,
    desc,
    or_,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from zenml.constants import (
    RESOURCE_POOL_UNBOUNDED_CAPACITY,
    RESOURCE_POOL_UNBOUNDED_KEYS,
)
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestStatus,
    StackComponentType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    ResourcePoolAllocation,
    ResourcePoolFilter,
    ResourcePoolQueueItem,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolSubjectPolicyFilter,
    ResourcePoolSubjectPolicyRequest,
    ResourcePoolSubjectPolicyResponse,
    ResourcePoolSubjectPolicyUpdate,
    ResourcePoolUpdate,
    ResourceRequestFilter,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ResourcePoolAllocationSchema,
    ResourcePoolQueueSchema,
    ResourcePoolResourceSchema,
    ResourcePoolSchema,
    ResourcePoolSubjectPolicyResourceSchema,
    ResourcePoolSubjectPolicySchema,
    ResourceRequestResourceSchema,
    ResourceRequestSchema,
    StackComponentSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.utils import (
    jl_arg,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import Session, SqlZenStore

logger = get_logger(__name__)


class ResourcePoolsSqlStore(ResourcePoolsStoreInterface):
    """Resource pools store implementation that uses SQL database backend."""

    store: "SqlZenStore"

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize the resource pools SQL store.

        Args:
            store: The store to use.
        """
        super().__init__()
        self.store = store

    # -------------------- Resource Pools -------------

    def _apply_resource_pool_capacity_updates(
        self,
        session: "Session",
        pool_id: UUID,
        capacity_updates: Dict[str, int],
    ) -> Tuple[bool, bool]:
        """Apply capacity updates to a pool.

        Args:
            session: DB session.
            pool_id: Pool ID to update.
            capacity_updates: Capacity values by key. A value of 0 removes the
                key from the pool.

        Returns:
            A tuple `(resources_decreased, resources_increased)` indicating
            whether at least one key moved down or up.
        """
        existing_resources_by_key = {
            resource.key: resource
            for resource in session.exec(
                select(ResourcePoolResourceSchema).where(
                    col(ResourcePoolResourceSchema.pool_id) == pool_id
                )
            ).all()
        }

        resources_decreased = False
        resources_increased = False
        for key, amount in capacity_updates.items():
            resource = existing_resources_by_key.get(key)
            if resource:
                if amount < resource.total:
                    resources_decreased = True
                elif amount > resource.total:
                    resources_increased = True

                if amount == 0:
                    session.delete(resource)
                else:
                    resource.total = amount
                    session.add(resource)
            elif amount > 0:
                resources_increased = True
                session.add(
                    ResourcePoolResourceSchema(
                        pool_id=pool_id,
                        key=key,
                        total=amount,
                        occupied=0,
                    )
                )

        return resources_decreased, resources_increased

    def _validate_resource_pool_capacity_update(
        self,
        session: "Session",
        pool_id: UUID,
        prospective_pool_capacity: Dict[str, int],
    ) -> None:
        """Validate a resource pool capacity update.

        Args:
            session: DB session.
            pool_id: Resource pool ID.
            prospective_pool_capacity: Prospective pool capacity.

        Raises:
            IllegalOperationError: If any attached policy would exceed the
                prospective capacity for reserved or limit resources.
        """
        policies = session.exec(
            select(ResourcePoolSubjectPolicySchema)
            .where(col(ResourcePoolSubjectPolicySchema.pool_id) == pool_id)
            .options(
                selectinload(jl_arg(ResourcePoolSubjectPolicySchema.resources))
            )
        ).all()

        policy_resource_rows: List[Tuple[UUID, str, int, Optional[int]]] = []
        for policy in policies:
            for resource in policy.resources:
                policy_resource_rows.append(
                    (
                        policy.component_id,
                        resource.key,
                        resource.reserved,
                        resource.limit,
                    )
                )

        reserved_sum_by_key = (
            self._validate_resource_rows_against_pool_capacity(
                policy_resource_rows=policy_resource_rows,
                pool_capacity=prospective_pool_capacity,
                operation="update pool capacity",
            )
        )
        self._validate_reserved_sum_by_key_against_pool_capacity(
            reserved_sum_by_key=reserved_sum_by_key,
            pool_capacity=prospective_pool_capacity,
            operation="update pool capacity",
        )

    def create_resource_pool(
        self, resource_pool: ResourcePoolRequest
    ) -> ResourcePoolResponse:
        """Create a resource pool.

        Args:
            resource_pool: The resource pool to create.

        Raises:
            EntityExistsError: If a resource pool with the same name already
                exists.

        Returns:
            The created resource pool.
        """
        with self.store.get_session() as session:
            self.store._set_request_user_id(
                request_model=resource_pool, session=session
            )

            new_resource_pool = ResourcePoolSchema.from_request(resource_pool)

            session.add(new_resource_pool)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise EntityExistsError(
                    "Unable to create resource pool: A resource pool with the "
                    f"name {resource_pool.name} already exists."
                )

            self._apply_resource_pool_capacity_updates(
                session=session,
                pool_id=new_resource_pool.id,
                capacity_updates=resource_pool.capacity,
            )

            session.commit()
            session.refresh(new_resource_pool)

            return new_resource_pool.to_model(
                include_metadata=True, include_resources=True
            )

    def get_resource_pool(
        self, resource_pool_id: UUID, hydrate: bool = True
    ) -> ResourcePoolResponse:
        """Get a resource pool by ID.

        Args:
            resource_pool_id: The ID of the resource pool to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The resource pool.
        """
        with self.store.get_session() as session:
            resource_pool = self.store._get_schema_by_id(
                resource_id=resource_pool_id,
                schema_class=ResourcePoolSchema,
                session=session,
                query_options=ResourcePoolSchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )
            return resource_pool.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_resource_pools(
        self, filter_model: ResourcePoolFilter, hydrate: bool = False
    ) -> Page[ResourcePoolResponse]:
        """List all resource pools matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all resource pools matching the filter criteria.
        """
        with self.store.get_session() as session:
            query = select(ResourcePoolSchema)
            return self.store.filter_and_paginate(
                session=session,
                query=query,
                table=ResourcePoolSchema,
                filter_model=filter_model,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
            )

    def list_resource_pool_queue_items(
        self,
        resource_pool_id: UUID,
    ) -> List[ResourcePoolQueueItem]:
        """List queued items for a resource pool.

        Args:
            resource_pool_id: The resource pool ID.

        Returns:
            Queue items in queue order.
        """
        with self.store.get_session() as session:
            self.store._get_schema_by_id(
                resource_id=resource_pool_id,
                schema_class=ResourcePoolSchema,
                session=session,
            )
            queue_items = session.exec(
                select(ResourcePoolQueueSchema)
                .where(
                    col(ResourcePoolQueueSchema.pool_id) == resource_pool_id
                )
                .join(
                    ResourceRequestSchema,
                    col(ResourceRequestSchema.id)
                    == col(ResourcePoolQueueSchema.request_id),
                )
                .where(
                    col(ResourceRequestSchema.status)
                    == ResourceRequestStatus.PENDING.value
                )
                .order_by(
                    desc(col(ResourcePoolQueueSchema.priority)),
                    col(ResourcePoolQueueSchema.request_created),
                    col(ResourcePoolQueueSchema.request_id),
                )
                .options(
                    selectinload(
                        jl_arg(ResourcePoolQueueSchema.request)
                    ).selectinload(
                        jl_arg(ResourceRequestSchema.requested_resources)
                    ),
                    selectinload(jl_arg(ResourcePoolQueueSchema.request))
                    .selectinload(jl_arg(ResourceRequestSchema.step_run))
                    .selectinload(jl_arg(StepRunSchema.pipeline_run)),
                    selectinload(
                        jl_arg(ResourcePoolQueueSchema.request)
                    ).selectinload(jl_arg(ResourceRequestSchema.user)),
                )
            ).all()

            # These might not be allocated in exactly that order, depending on
            # the resources that get freed. But this is the best we can do
            # without actually running the very expensive allocator query.
            return [
                ResourcePoolQueueItem(
                    request=item.request.to_model(
                        include_metadata=True, include_resources=True
                    ),
                    priority=item.priority,
                )
                for item in queue_items
            ]

    def list_resource_pool_allocations(
        self,
        resource_pool_id: UUID,
    ) -> List[ResourcePoolAllocation]:
        """List active allocations for a resource pool.

        Args:
            resource_pool_id: The resource pool ID.

        Returns:
            Active allocations in allocation order.
        """
        with self.store.get_session() as session:
            self.store._get_schema_by_id(
                resource_id=resource_pool_id,
                schema_class=ResourcePoolSchema,
                session=session,
            )
            allocations = session.exec(
                select(ResourcePoolAllocationSchema)
                .where(
                    col(ResourcePoolAllocationSchema.pool_id)
                    == resource_pool_id
                )
                .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
                .order_by(
                    col(ResourcePoolAllocationSchema.allocated_at),
                    col(ResourcePoolAllocationSchema.request_id),
                )
                .options(
                    selectinload(
                        jl_arg(ResourcePoolAllocationSchema.request)
                    ).selectinload(
                        jl_arg(ResourceRequestSchema.requested_resources)
                    ),
                    selectinload(jl_arg(ResourcePoolAllocationSchema.request))
                    .selectinload(jl_arg(ResourceRequestSchema.step_run))
                    .selectinload(jl_arg(StepRunSchema.pipeline_run)),
                    selectinload(
                        jl_arg(ResourcePoolAllocationSchema.request)
                    ).selectinload(jl_arg(ResourceRequestSchema.user)),
                    selectinload(
                        jl_arg(ResourcePoolAllocationSchema.policy)
                    ).selectinload(
                        jl_arg(ResourcePoolSubjectPolicySchema.resources)
                    ),
                )
            ).all()
            borrowed_resources = self._get_borrowed_resources_per_allocation(
                allocations=allocations
            )
            return [
                ResourcePoolAllocation(
                    request=allocation.request.to_model(
                        include_metadata=True, include_resources=True
                    ),
                    priority=allocation.priority,
                    allocated_at=allocation.allocated_at,
                    borrowed_resources=borrowed_resources.get(
                        allocation.id, {}
                    ),
                )
                for allocation in allocations
            ]

    def _get_borrowed_resources_per_allocation(
        self,
        allocations: Sequence[ResourcePoolAllocationSchema],
    ) -> Dict[UUID, Dict[str, int]]:
        """Compute borrowed resources per allocation from loaded schemas."""
        current_usage_by_policy: Dict[UUID, Dict[str, int]] = {}
        borrowed_by_allocation: Dict[UUID, Dict[str, int]] = {}

        for allocation in allocations:
            if allocation.policy is None:
                continue

            policy_id = allocation.policy.id
            reserved_resources = {
                resource.key: resource.reserved
                for resource in allocation.policy.resources
            }
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

    def update_resource_pool(
        self, resource_pool_id: UUID, update: ResourcePoolUpdate
    ) -> ResourcePoolResponse:
        """Update an existing resource pool.

        Args:
            resource_pool_id: The ID of the resource pool to update.
            update: The update to be applied to the resource pool.

        Returns:
            The updated resource pool.
        """
        with self.store.get_session() as session:
            existing_resource_pool = self.store._get_schema_by_id(
                resource_id=resource_pool_id,
                schema_class=ResourcePoolSchema,
                session=session,
            )

            existing_resource_pool.update(update)
            session.add(existing_resource_pool)
            session.commit()

            if update.capacity:
                self._acquire_resource_pool_lock(
                    session,
                    pool_id=existing_resource_pool.id,
                )

                current_capacity_by_key = dict(
                    session.exec(
                        select(
                            col(ResourcePoolResourceSchema.key),
                            col(ResourcePoolResourceSchema.total),
                        ).where(
                            col(ResourcePoolResourceSchema.pool_id)
                            == existing_resource_pool.id
                        )
                    ).all()
                )
                prospective_capacity = dict(current_capacity_by_key)
                for key, amount in update.capacity.items():
                    if amount == 0:
                        prospective_capacity.pop(key, None)
                    else:
                        prospective_capacity[key] = amount

                self._validate_resource_pool_capacity_update(
                    session=session,
                    pool_id=existing_resource_pool.id,
                    prospective_pool_capacity=prospective_capacity,
                )

                resources_decreased, resources_increased = (
                    self._apply_resource_pool_capacity_updates(
                        session=session,
                        pool_id=existing_resource_pool.id,
                        capacity_updates=update.capacity,
                    )
                )
                session.commit()

                if resources_decreased:
                    self._rebuild_resource_pool_request_queue(
                        session=session, pool_id=existing_resource_pool.id
                    )
                    session.commit()

                if resources_increased:
                    self._allocate_queued_requests_for_pool(
                        session=session, pool_id=existing_resource_pool.id
                    )
                    session.commit()

                session.refresh(existing_resource_pool)

            return existing_resource_pool.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_resource_pool(self, resource_pool_id: UUID) -> None:
        """Delete a resource pool.

        Args:
            resource_pool_id: The ID of the resource pool to delete.

        Raises:
            IllegalOperationError: If the pool still has queued or allocated
                requests.
        """
        with self.store.get_session() as session:
            self.store._get_schema_by_id(
                resource_id=resource_pool_id,
                schema_class=ResourcePoolSchema,
                session=session,
            )
            # Serialize with allocators for this pool before checking for active
            # queue/allocation entries to avoid check-then-delete races.
            self._acquire_resource_pool_lock(
                session=session, pool_id=resource_pool_id
            )
            queued_count = session.exec(
                select(func.count())
                .select_from(ResourcePoolQueueSchema)
                .where(
                    col(ResourcePoolQueueSchema.pool_id) == resource_pool_id
                )
            ).one()
            allocated_count = session.exec(
                select(func.count())
                .select_from(ResourcePoolAllocationSchema)
                .where(
                    col(ResourcePoolAllocationSchema.pool_id)
                    == resource_pool_id
                )
                .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
            ).one()
            if queued_count or allocated_count:
                raise IllegalOperationError(
                    "Unable to delete resource pool while requests are still "
                    f"active (queued={queued_count}, "
                    f"allocated={allocated_count})."
                )
            session.execute(
                delete(ResourcePoolSchema).where(
                    col(ResourcePoolSchema.id) == resource_pool_id
                )
            )
            self._reject_requests_not_in_queue(session)
            session.commit()

    def create_resource_pool_subject_policy(
        self, policy: ResourcePoolSubjectPolicyRequest
    ) -> ResourcePoolSubjectPolicyResponse:
        """Create a resource pool subject policy.

        Args:
            policy: The policy to create.

        Returns:
            The created policy.
        """
        with self.store.get_session() as session:
            self.store._set_request_user_id(
                request_model=policy, session=session
            )
            component = self.store._get_schema_by_id(
                resource_id=policy.component_id,
                schema_class=StackComponentSchema,
                session=session,
            )
            if component.type not in {
                StackComponentType.ORCHESTRATOR.value,
                StackComponentType.STEP_OPERATOR.value,
            }:
                raise IllegalOperationError(
                    "Resource pool policies can only be attached to "
                    "orchestrators and step operators."
                )

            created_policy = self._create_resource_pool_subject_policy(
                session=session,
                policy=policy,
                resource_pool_id=policy.pool_id,
            )
            try:
                session.commit()
            except IntegrityError:
                raise EntityExistsError(
                    "Unable to create policy: The component is already "
                    "attached to the resource pool."
                )

            self._enqueue_pending_requests_for_component_into_pool(
                session=session,
                component_id=policy.component_id,
                pool_id=policy.pool_id,
                priority=policy.priority,
            )
            session.commit()

            return created_policy.to_model(
                include_metadata=True, include_resources=True
            )

    def get_resource_pool_subject_policy(
        self, policy_id: UUID, hydrate: bool = True
    ) -> ResourcePoolSubjectPolicyResponse:
        """Get a resource pool subject policy by ID.

        Args:
            policy_id: The policy ID.
            hydrate: Whether to include metadata fields.

        Returns:
            The requested policy.
        """
        with self.store.get_session() as session:
            policy = self.store._get_schema_by_id(
                resource_id=policy_id,
                schema_class=ResourcePoolSubjectPolicySchema,
                session=session,
                query_options=ResourcePoolSubjectPolicySchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )
            return policy.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_resource_pool_subject_policies(
        self,
        filter_model: ResourcePoolSubjectPolicyFilter,
        hydrate: bool = False,
    ) -> Page[ResourcePoolSubjectPolicyResponse]:
        """List resource pool subject policies.

        Args:
            filter_model: Pagination and filter model.
            hydrate: Whether to include metadata fields.

        Returns:
            Matching policies.
        """
        with self.store.get_session() as session:
            query = select(ResourcePoolSubjectPolicySchema)
            return self.store.filter_and_paginate(
                session=session,
                query=query,
                table=ResourcePoolSubjectPolicySchema,
                filter_model=filter_model,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
            )

    def update_resource_pool_subject_policy(
        self, policy_id: UUID, update: ResourcePoolSubjectPolicyUpdate
    ) -> ResourcePoolSubjectPolicyResponse:
        """Update a resource pool subject policy.

        Args:
            policy_id: The ID of the policy to update.
            update: The update model.

        Returns:
            The updated policy.
        """
        with self.store.get_session() as session:
            existing_policy = self.store._get_schema_by_id(
                resource_id=policy_id,
                schema_class=ResourcePoolSubjectPolicySchema,
                session=session,
            )
            self._acquire_resource_pool_lock(
                session=session, pool_id=existing_policy.pool_id
            )

            if update.priority is not None:
                existing_policy.priority = update.priority

            if update.reserved is not None or update.limit is not None:
                reserved_by_key = (
                    update.reserved
                    if update.reserved is not None
                    else {
                        resource.key: resource.reserved
                        for resource in existing_policy.resources
                    }
                )
                limit_by_key = (
                    update.limit
                    if update.limit is not None
                    else {
                        resource.key: resource.limit
                        for resource in existing_policy.resources
                        if resource.limit is not None
                    }
                )

                (
                    pool_capacity_by_key,
                    all_keys,
                ) = self._validate_policy_resources_against_pool_capacity(
                    session=session,
                    pool_id=existing_policy.pool_id,
                    reserved=reserved_by_key,
                    limit=limit_by_key,
                    operation="update",
                )

                session.execute(
                    delete(ResourcePoolSubjectPolicyResourceSchema).where(
                        col(ResourcePoolSubjectPolicyResourceSchema.policy_id)
                        == existing_policy.id
                    )
                )
                session.flush()

                for key in all_keys:
                    session.add(
                        ResourcePoolSubjectPolicyResourceSchema(
                            policy_id=existing_policy.id,
                            key=key,
                            reserved=reserved_by_key.get(key, 0),
                            limit=limit_by_key.get(key),
                        )
                    )

                self._validate_policy_reserved_resources_sum(
                    session=session,
                    pool_id=existing_policy.pool_id,
                    resource_keys=all_keys,
                    pool_capacity=pool_capacity_by_key,
                    operation="update",
                )

            existing_policy.updated = utc_now()
            session.add(existing_policy)
            session.commit()

            session.refresh(existing_policy)

            self._rebuild_resource_pool_request_queue(
                session=session, pool_id=existing_policy.pool_id
            )
            self._allocate_queued_requests_for_pool(
                session=session, pool_id=existing_policy.pool_id
            )
            self._reject_requests_not_in_queue(session=session)
            session.commit()

            return existing_policy.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_resource_pool_subject_policy(self, policy_id: UUID) -> None:
        """Delete a resource pool subject policy.

        Args:
            policy_id: The ID of the policy to delete.

        Raises:
            IllegalOperationError: If the policy still has queued or allocated
                requests in the pool.
        """
        with self.store.get_session() as session:
            policy = self.store._get_schema_by_id(
                resource_id=policy_id,
                schema_class=ResourcePoolSubjectPolicySchema,
                session=session,
            )
            self._acquire_resource_pool_lock(
                session=session, pool_id=policy.pool_id
            )

            queued_count = session.exec(
                select(func.count())
                .select_from(ResourcePoolQueueSchema)
                .join(
                    ResourceRequestSchema,
                    col(ResourceRequestSchema.id)
                    == col(ResourcePoolQueueSchema.request_id),
                )
                .where(col(ResourcePoolQueueSchema.pool_id) == policy.pool_id)
                .where(
                    col(ResourceRequestSchema.component_id)
                    == policy.component_id
                )
            ).one()
            allocated_count = session.exec(
                select(func.count())
                .select_from(ResourcePoolAllocationSchema)
                .join(
                    ResourceRequestSchema,
                    col(ResourceRequestSchema.id)
                    == col(ResourcePoolAllocationSchema.request_id),
                )
                .where(
                    col(ResourcePoolAllocationSchema.pool_id) == policy.pool_id
                )
                .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
                .where(
                    col(ResourceRequestSchema.component_id)
                    == policy.component_id
                )
            ).one()

            if queued_count or allocated_count:
                raise IllegalOperationError(
                    "Unable to delete policy while requests are still actively "
                    f"using it (queued={queued_count}, "
                    f"allocated={allocated_count})."
                )

            session.execute(
                delete(ResourcePoolSubjectPolicySchema).where(
                    col(ResourcePoolSubjectPolicySchema.component_id)
                    == policy.component_id,
                    col(ResourcePoolSubjectPolicySchema.pool_id)
                    == policy.pool_id,
                )
            )

            self._reject_requests_not_in_queue(session=session)
            session.commit()

    def _create_resource_pool_subject_policy(
        self,
        session: "Session",
        policy: ResourcePoolSubjectPolicyRequest,
        resource_pool_id: UUID,
    ) -> ResourcePoolSubjectPolicySchema:
        """Create a subject policy for a resource pool.

        Args:
            session: DB session.
            policy: The policy to create.
            resource_pool_id: The ID of the resource pool.

        Raises:
            IllegalOperationError: If the policy cannot be created because
                some resources exceed the pools capacity.

        Returns:
            The created policy schema.
        """
        # Make sure the pool exists
        self.store._get_schema_by_id(
            resource_id=resource_pool_id,
            schema_class=ResourcePoolSchema,
            session=session,
        )

        all_reserved = policy.reserved or {}
        all_limit = policy.limit or {}
        (
            pool_capacity_by_key,
            all_keys,
        ) = self._validate_policy_resources_against_pool_capacity(
            session=session,
            pool_id=resource_pool_id,
            reserved=all_reserved,
            limit=all_limit,
            operation="create",
        )

        policy_schema = ResourcePoolSubjectPolicySchema(
            user_id=policy.user,
            component_id=policy.component_id,
            pool_id=resource_pool_id,
            priority=policy.priority,
        )
        session.add(policy_schema)
        session.flush()

        for key in all_keys:
            policy_resource = ResourcePoolSubjectPolicyResourceSchema(
                policy_id=policy_schema.id,
                key=key,
                reserved=all_reserved.get(key, 0),
                limit=all_limit.get(key),
            )
            session.add(policy_resource)

        self._validate_policy_reserved_resources_sum(
            session=session,
            pool_id=resource_pool_id,
            resource_keys=all_keys,
            pool_capacity=pool_capacity_by_key,
            operation="create",
        )
        return policy_schema

    def _validate_policy_resources_against_pool_capacity(
        self,
        session: "Session",
        pool_id: UUID,
        reserved: Mapping[str, int],
        limit: Mapping[str, Optional[int]],
        operation: str,
    ) -> Tuple[Dict[str, int], Set[str]]:
        """Validate policy resources against pool capacity.

        Args:
            session: DB session.
            pool_id: The resource pool ID.
            reserved: Reserved resources.
            limit: Resource limis.
            operation: Operation name for error messages.

        Raises:
            IllegalOperationError: If values exceed pool capacity or key is
                missing in pool capacity.

        Returns:
            A tuple `(pool_capacity, resource_keys)`.
        """
        pool_capacity_by_key = dict(
            session.exec(
                select(
                    col(ResourcePoolResourceSchema.key),
                    col(ResourcePoolResourceSchema.total),
                ).where(col(ResourcePoolResourceSchema.pool_id) == pool_id)
            ).all()
        )
        resource_keys = set(reserved.keys()) | set(limit.keys())
        self._validate_resource_rows_against_pool_capacity(
            policy_resource_rows=[
                (None, key, reserved.get(key, 0), limit.get(key))
                for key in resource_keys
            ],
            pool_capacity=pool_capacity_by_key,
            operation=operation,
        )
        return pool_capacity_by_key, resource_keys

    def _validate_policy_reserved_resources_sum(
        self,
        session: "Session",
        pool_id: UUID,
        resource_keys: Set[str],
        pool_capacity: Dict[str, int],
        operation: str,
    ) -> None:
        """Validate total reserved resources across all policies in a pool.

        Args:
            session: DB session.
            pool_id: The resource pool ID.
            resource_keys: Resource keys to validate.
            pool_capacity: Pool capacity by key.
            operation: Operation name for error messages.

        Raises:
            IllegalOperationError: If sum of reserved resources exceeds pool
                capacity for any key.
        """
        if not resource_keys:
            return

        reserved_sums_by_key = dict(
            session.exec(
                select(
                    col(ResourcePoolSubjectPolicyResourceSchema.key),
                    func.sum(
                        col(ResourcePoolSubjectPolicyResourceSchema.reserved)
                    ),
                )
                .join(
                    ResourcePoolSubjectPolicySchema,
                    col(ResourcePoolSubjectPolicySchema.id)
                    == col(ResourcePoolSubjectPolicyResourceSchema.policy_id),
                )
                .where(col(ResourcePoolSubjectPolicySchema.pool_id) == pool_id)
                .where(
                    col(ResourcePoolSubjectPolicyResourceSchema.key).in_(
                        resource_keys
                    )
                )
                .group_by(col(ResourcePoolSubjectPolicyResourceSchema.key))
            ).all()
        )
        self._validate_reserved_sum_by_key_against_pool_capacity(
            reserved_sum_by_key={
                key: (reserved_sum or 0)
                for key, reserved_sum in reserved_sums_by_key.items()
            },
            pool_capacity=pool_capacity,
            operation=operation,
        )

    def _validate_resource_rows_against_pool_capacity(
        self,
        policy_resource_rows: Sequence[
            Tuple[Optional[UUID], str, int, Optional[int]]
        ],
        pool_capacity: Dict[str, int],
        operation: str,
    ) -> Dict[str, int]:
        """Validate resource rows against pool capacity.

        Args:
            policy_resource_rows: Tuples of
                `(component_id, key, reserved, limit)`.
            pool_capacity: Pool capacity keyed by resource key.
            operation: Operation name used in error messages.

        Raises:
            IllegalOperationError: If a key is missing in the pool, or reserved
                or limit exceed pool capacity.

        Returns:
            Reserved sums by key.
        """
        reserved_sum_by_key: Dict[str, int] = {}
        for component_id, key, reserved, limit in policy_resource_rows:
            total_capacity = pool_capacity.get(key)
            if total_capacity is None:
                component_message = (
                    f" for component `{component_id}`"
                    if component_id is not None
                    else ""
                )
                raise IllegalOperationError(
                    f"Unable to {operation}: Resource key `{key}`{component_message} "
                    "is not defined in pool capacity."
                )

            if reserved > total_capacity:
                component_message = (
                    f" for component `{component_id}`"
                    if component_id is not None
                    else ""
                )
                raise IllegalOperationError(
                    f"Unable to {operation}: Reserved amount `{reserved}` for "
                    f"key `{key}`{component_message} exceeds pool capacity "
                    f"`{total_capacity}`."
                )

            if limit is not None and limit > total_capacity:
                component_message = (
                    f" for component `{component_id}`"
                    if component_id is not None
                    else ""
                )
                raise IllegalOperationError(
                    f"Unable to {operation}: Limit `{limit}` for key `{key}`"
                    f"{component_message} exceeds pool capacity "
                    f"`{total_capacity}`."
                )

            reserved_sum_by_key[key] = (
                reserved_sum_by_key.get(key, 0) + reserved
            )

        return reserved_sum_by_key

    def _validate_reserved_sum_by_key_against_pool_capacity(
        self,
        reserved_sum_by_key: Dict[str, int],
        pool_capacity: Dict[str, int],
        operation: str,
    ) -> None:
        """Validate reserved sums against pool capacity.

        Args:
            reserved_sum_by_key: Reserved sums by key.
            pool_capacity: Pool capacity by key.
            operation: Operation name used in error messages.

        Raises:
            IllegalOperationError: If reserved sum exceeds pool capacity.
        """
        for key, reserved_sum in reserved_sum_by_key.items():
            total_capacity = pool_capacity[key]
            if reserved_sum > total_capacity:
                raise IllegalOperationError(
                    f"Unable to {operation}: Sum of reserved amounts for key "
                    f"`{key}` ({reserved_sum}) exceeds pool capacity "
                    f"({total_capacity})."
                )

    # -------------------- Resource Requests -------------

    def create_resource_request(
        self, resource_request: ResourceRequestRequest
    ) -> ResourceRequestResponse:
        """Create a resource request.

        Args:
            resource_request: The resource request to create.

        Returns:
            The created resource request.
        """
        with self.store.get_session() as session:
            self.store._set_request_user_id(
                request_model=resource_request, session=session
            )

            new_resource_request = ResourceRequestSchema.from_request(
                resource_request
            )

            session.add(new_resource_request)
            session.commit()

            for key, amount in resource_request.requested_resources.items():
                resource_request_resource = ResourceRequestResourceSchema(
                    request_id=new_resource_request.id,
                    key=key,
                    amount=amount,
                )
                session.add(resource_request_resource)
            session.commit()
            session.refresh(new_resource_request)

            self._enqueue_resource_request(
                session=session, resource_request=new_resource_request
            )
            session.commit()
            session.refresh(new_resource_request)

            return new_resource_request.to_model(
                include_metadata=True, include_resources=True
            )

    def get_resource_request(
        self, resource_request_id: UUID, hydrate: bool = True
    ) -> ResourceRequestResponse:
        """Get a resource request by ID.

        Args:
            resource_request_id: The ID of the resource request to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The resource request.
        """
        with self.store.get_session() as session:
            resource_request = self.store._get_schema_by_id(
                resource_id=resource_request_id,
                schema_class=ResourceRequestSchema,
                session=session,
                query_options=ResourceRequestSchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )
            return resource_request.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_resource_requests(
        self, filter_model: ResourceRequestFilter, hydrate: bool = False
    ) -> Page[ResourceRequestResponse]:
        """List all resource requests matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all resource requests matching the filter criteria.
        """
        with self.store.get_session() as session:
            query = select(ResourceRequestSchema)
            return self.store.filter_and_paginate(
                session=session,
                query=query,
                table=ResourceRequestSchema,
                filter_model=filter_model,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
            )

    def update_resource_request(
        self, resource_request_id: UUID, update: ResourceRequestUpdate
    ) -> ResourceRequestResponse:
        """Update an existing resource request.

        Args:
            resource_request_id: The ID of the resource request to update.
            update: The update to be applied to the resource request.

        Returns:
            The updated resource request.
        """
        with self.store.get_session() as session:
            existing_resource_request = self.store._get_schema_by_id(
                resource_id=resource_request_id,
                schema_class=ResourceRequestSchema,
                session=session,
            )

            existing_resource_request.update(update)
            session.add(existing_resource_request)
            session.commit()

            return existing_resource_request.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_resource_request(self, resource_request_id: UUID) -> None:
        """Delete a resource request.

        Args:
            resource_request_id: The ID of the resource request to delete.
        """
        with self.store.get_session() as session:
            resource_request = self.store._get_schema_by_id(
                resource_id=resource_request_id,
                schema_class=ResourceRequestSchema,
                session=session,
            )
            self._release_request_resources(session, resource_request)
            session.delete(resource_request)
            session.commit()

    def _enqueue_resource_request(
        self, session: "Session", resource_request: ResourceRequestSchema
    ) -> None:
        """Enqueue a request into all pools it can fit in.

        Requests are only enqueued in a pool if they fit into the pool's
        total capacity (ignoring current occupancy).

        Args:
            session: DB session.
            resource_request: The resource request to enqueue.
        """
        if resource_request.status != ResourceRequestStatus.PENDING.value:
            return

        policies = session.exec(
            select(ResourcePoolSubjectPolicySchema)
            .where(
                ResourcePoolSubjectPolicySchema.component_id
                == resource_request.component_id
            )
            .order_by(
                desc(ResourcePoolSubjectPolicySchema.priority),
                col(ResourcePoolSubjectPolicySchema.pool_id),
            )
        ).all()

        if not policies:
            # There are no policies assigned to the component. This means ZenML
            # isn't responsible for managing resources for this component, so
            # we approve the request immediately.
            self._set_resource_request_status(
                session=session,
                resource_request=resource_request,
                status=ResourceRequestStatus.ALLOCATED,
            )
            return

        for policy in policies:
            pool_violation = session.exec(
                self._fits_pool_violation_subquery(
                    pool_id=policy.pool_id,
                    component_id=resource_request.component_id,
                    request_id_expression=resource_request.id,
                    preemptable_expression=resource_request.preemptable,
                )
            ).first()
            if pool_violation is not None:
                continue

            self._enqueue_request_into_pool_queue(
                session=session,
                pool_id=policy.pool_id,
                request_id=resource_request.id,
                priority=policy.priority,
                request_created=resource_request.created,
            )

        queued_anywhere = session.exec(
            select(ResourcePoolQueueSchema.id)
            .where(
                col(ResourcePoolQueueSchema.request_id) == resource_request.id
            )
            .limit(1)
        ).first()
        if queued_anywhere is None:
            rejection_reason = (
                f"The requested resources exceed the {'reserved resources' if not resource_request.preemptable else 'resources'} available in all "
                "attached resource pool policies."
            )
            self._set_resource_request_status(
                session=session,
                resource_request=resource_request,
                status=ResourceRequestStatus.REJECTED,
                status_reason=rejection_reason,
            )
            return

        if resource_request.status == ResourceRequestStatus.PENDING.value:
            # After enqueuing the request, check if the request can be allocated
            # in any of the pools immediately
            #
            # This allocation attempt uses a pool-level row lock as a mutex.
            # Commit the queue inserts first so we don't hold queue locks while
            # acquiring the pool lock (avoids lock-order inversion/deadlocks
            # under concurrent enqueues/allocations).
            session.commit()
            queued_pool_ids = session.exec(
                select(ResourcePoolQueueSchema.pool_id)
                .where(
                    col(ResourcePoolQueueSchema.request_id)
                    == resource_request.id
                )
                .order_by(
                    desc(ResourcePoolQueueSchema.priority),
                    col(ResourcePoolQueueSchema.request_created),
                    col(ResourcePoolQueueSchema.pool_id),
                )
            ).all()

            for pool_id in queued_pool_ids:
                self._allocate_queued_requests_for_pool(
                    session=session, pool_id=pool_id, max_allocations=10
                )
                session.commit()
                session.refresh(resource_request)
                if (
                    resource_request.status
                    != ResourceRequestStatus.PENDING.value
                ):
                    break
        session.refresh(resource_request)

    def _enqueue_pending_requests_for_component_into_pool(
        self,
        session: "Session",
        component_id: UUID,
        pool_id: UUID,
        priority: int,
    ) -> None:
        """Enqueue all pending requests for a component into a pool if eligible.

        This is used when a pool is attached to a component: any already pending
        requests should become eligible for acquisition in the new pool if the
        pool has sufficient total capacity.

        Args:
            session: DB session.
            component_id: The component whose pending requests should be enqueued.
            pool_id: The pool into which requests should be enqueued.
            priority: The component's priority for this pool.
        """
        fits_pool_violation = self._fits_pool_violation_subquery(
            pool_id=pool_id,
            component_id=component_id,
            request_id_expression=col(ResourceRequestSchema.id),
            preemptable_expression=col(ResourceRequestSchema.preemptable),
        )

        already_enqueued = select(ResourcePoolQueueSchema.id).where(
            col(ResourcePoolQueueSchema.pool_id) == pool_id,
            col(ResourcePoolQueueSchema.request_id)
            == col(ResourceRequestSchema.id),
        )

        eligible_requests = session.exec(
            select(ResourceRequestSchema.id, ResourceRequestSchema.created)
            .where(col(ResourceRequestSchema.component_id) == component_id)
            .where(
                col(ResourceRequestSchema.status)
                == ResourceRequestStatus.PENDING.value
            )
            .where(~exists(fits_pool_violation))
            .where(~exists(already_enqueued))
            .order_by(
                col(ResourceRequestSchema.created),
                col(ResourceRequestSchema.id),
            )
        ).all()

        if not eligible_requests:
            return

        for request_id, created_at in eligible_requests:
            self._enqueue_request_into_pool_queue(
                session=session,
                pool_id=pool_id,
                request_id=request_id,
                priority=priority,
                request_created=created_at,
            )

        # Try allocating now that we've added new eligible requests into the
        # queue.
        # Commit the inserts first so allocation can take the pool mutex before
        # acquiring any queue row locks.
        session.commit()
        self._allocate_queued_requests_for_pool(
            session=session, pool_id=pool_id, max_allocations=10
        )

    @staticmethod
    def _enqueue_request_into_pool_queue(
        session: "Session",
        pool_id: UUID,
        request_id: UUID,
        priority: int,
        request_created: datetime,
    ) -> bool:
        """Insert a request into a request pool queue.

        Args:
            session: DB session.
            pool_id: The ID of the pool to enqueue the request into.
            request_id: The ID of the request to enqueue.
            priority: The priority of the request within that queue.
            request_created: The creation time of the request.

        Returns:
            True if the request was inserted successfully, False if someone else
            enqueued the same request concurrently.
        """
        try:
            with session.begin_nested():
                session.add(
                    ResourcePoolQueueSchema(
                        pool_id=pool_id,
                        request_id=request_id,
                        priority=priority,
                        request_created=request_created,
                    )
                )
                session.flush()
        except IntegrityError:
            # Someone else may have enqueued concurrently.
            return False
        return True

    @staticmethod
    def _set_resource_request_status(
        session: "Session",
        resource_request: ResourceRequestSchema,
        status: ResourceRequestStatus,
        status_reason: Optional[str] = None,
        preemption_initiated_by_id: Optional[UUID] = None,
        updated: Optional[datetime] = None,
    ) -> None:
        """Apply a status transition to an ORM request object.

        Args:
            session: DB session.
            resource_request: ORM request object to update.
            status: New request status.
            status_reason: Optional reason attached to the status.
            preemption_initiated_by_id: Optional request ID that initiated
                preemption.
            updated: Optional timestamp. If not provided, current UTC time is
                used.
        """
        resource_request.status = status.value
        resource_request.updated = updated or utc_now()
        if status_reason is not None:
            resource_request.status_reason = status_reason
        if preemption_initiated_by_id is not None:
            resource_request.preemption_initiated_by_id = (
                preemption_initiated_by_id
            )
        session.add(resource_request)

    @staticmethod
    def _attempt_resource_request_status_transition(
        session: "Session",
        request_id: UUID,
        new_status: ResourceRequestStatus,
        expected_status: Optional[ResourceRequestStatus] = None,
        status_reason: Optional[str] = None,
        preemption_initiated_by_id: Optional[UUID] = None,
        updated: Optional[datetime] = None,
    ) -> bool:
        """Attempt a resource request status transition.

        Args:
            session: DB session.
            request_id: ID of the request to update.
            new_status: Target status.
            expected_status: Optional allowed current status. If provided,
                the transition only succeeds when the current status is the
                expected status.
            status_reason: Optional reason attached to the status.
            preemption_initiated_by_id: Optional request ID that initiated
                preemption.
            updated: Optional timestamp. If not provided, current UTC time is
                used.

        Returns:
            True if the transition was applied, False otherwise.
        """
        query = update(ResourceRequestSchema).where(
            col(ResourceRequestSchema.id) == request_id
        )
        if expected_status:
            query = query.where(
                col(ResourceRequestSchema.status) == expected_status.value
            )

        values: Dict[str, Any] = {
            "status": new_status.value,
            "updated": updated or utc_now(),
        }
        if status_reason is not None:
            values["status_reason"] = status_reason
        if preemption_initiated_by_id is not None:
            values["preemption_initiated_by_id"] = preemption_initiated_by_id

        result = session.execute(query.values(**values))
        return result.rowcount == 1  # type: ignore[attr-defined, no-any-return]

    @staticmethod
    def _effective_pool_total_expression(
        resource_key_expression: Any,
    ) -> Any:
        """Build effective pool total expression with key-based defaults.

        Args:
            resource_key_expression: SQL expression that resolves to a resource
                key.

        Returns:
            SQL expression for effective pool total capacity.
        """
        return func.coalesce(
            ResourcePoolResourceSchema.total,
            case(
                (
                    resource_key_expression.in_(RESOURCE_POOL_UNBOUNDED_KEYS),
                    RESOURCE_POOL_UNBOUNDED_CAPACITY,
                ),
                else_=0,
            ),
        )

    @staticmethod
    def _effective_policy_limit_expression(
        resource_key_expression: Any,
    ) -> Any:
        """Build effective policy limit expression with pool fallback.

        Args:
            resource_key_expression: SQL expression that resolves to a resource
                key.

        Returns:
            SQL expression for effective policy limit.
        """
        return func.coalesce(
            ResourcePoolSubjectPolicyResourceSchema.limit,
            ResourcePoolsSqlStore._effective_pool_total_expression(
                resource_key_expression=resource_key_expression,
            ),
        )

    @staticmethod
    def _fits_pool_violation_subquery(
        pool_id: UUID,
        component_id: UUID,
        request_id_expression: Any,
        preemptable_expression: Any = True,
    ) -> SelectOfScalar[UUID]:
        """Subquery that checks if a request fits into a pool given its policy.

        The returned subquery yields a row if at least one requested resource
        key/amount violates any of the following constraints:

        - The effective pool total capacity for the key is smaller than the
          requested amount
        - The component policy limit for the key is smaller than the requested
          amount
        - The request is non-preemptable and exceeds the reserved policy share

        Missing limit configuration defaults to the pool total capacity for that
        resource key. For keys in `RESOURCE_POOL_UNBOUNDED_KEYS`, missing pool
        capacity defaults to an effectively unbounded value.

        Args:
            pool_id: The ID of the pool to check.
            component_id: The component ID for which to check the policy.
            request_id_expression: The expression for the request ID.
            preemptable_expression: Whether the request is preemptable. Can be
                either a Python bool or a SQL expression.

        Returns:
            The subquery.
        """
        resource_key_expr = col(ResourceRequestResourceSchema.key)
        effective_pool_total_expr = (
            ResourcePoolsSqlStore._effective_pool_total_expression(
                resource_key_expression=resource_key_expr,
            )
        )
        effective_max_expr = (
            ResourcePoolsSqlStore._effective_policy_limit_expression(
                resource_key_expression=resource_key_expr,
            )
        )
        if isinstance(preemptable_expression, bool):
            reserved_violation_condition: Any = (
                col(ResourceRequestResourceSchema.amount)
                > func.coalesce(
                    col(ResourcePoolSubjectPolicyResourceSchema.reserved), 0
                )
                if preemptable_expression is False
                else False
            )
        else:
            reserved_violation_condition = and_(
                ~preemptable_expression,
                col(ResourceRequestResourceSchema.amount)
                > func.coalesce(
                    col(ResourcePoolSubjectPolicyResourceSchema.reserved), 0
                ),
            )

        return (
            select(ResourceRequestResourceSchema.id)
            .select_from(ResourceRequestResourceSchema)
            .outerjoin(
                ResourcePoolSubjectPolicySchema,
                and_(
                    col(ResourcePoolSubjectPolicySchema.pool_id) == pool_id,
                    col(ResourcePoolSubjectPolicySchema.component_id)
                    == component_id,
                ),
            )
            .outerjoin(
                ResourcePoolSubjectPolicyResourceSchema,
                and_(
                    col(ResourcePoolSubjectPolicyResourceSchema.policy_id)
                    == col(ResourcePoolSubjectPolicySchema.id),
                    col(ResourcePoolSubjectPolicyResourceSchema.key)
                    == col(ResourceRequestResourceSchema.key),
                ),
            )
            .outerjoin(
                ResourcePoolResourceSchema,
                and_(
                    col(ResourcePoolResourceSchema.pool_id) == pool_id,
                    col(ResourcePoolResourceSchema.key)
                    == col(ResourceRequestResourceSchema.key),
                ),
            )
            .where(
                ResourceRequestResourceSchema.request_id
                == request_id_expression
            )
            .where(col(ResourceRequestResourceSchema.amount) > 0)
            .where(
                or_(
                    effective_pool_total_expr
                    < col(ResourceRequestResourceSchema.amount),
                    effective_max_expr
                    < col(ResourceRequestResourceSchema.amount),
                    reserved_violation_condition,
                )
            )
            .limit(1)
        )

    def _rebuild_resource_pool_request_queue(
        self, session: "Session", pool_id: UUID
    ) -> None:
        """Rebuild the request queue after the pools resources changed.

        We maintain the queue such that all queued requests are eligible
        with respect to the pool's total capacity.

        Args:
            session: DB session.
            pool_id: The ID of the pool to rebuild the request queue for.
        """
        # Acquire the pool lock first to keep lock ordering consistent with the
        # allocator and release paths.
        if not self._acquire_resource_pool_lock(session, pool_id=pool_id):
            return

        # First delete the entire queue for this pool
        session.execute(
            delete(ResourcePoolQueueSchema).where(
                col(ResourcePoolQueueSchema.pool_id) == pool_id
            )
        )
        policies = session.exec(
            select(ResourcePoolSubjectPolicySchema).where(
                ResourcePoolSubjectPolicySchema.pool_id == pool_id
            )
        ).all()
        session.flush()

        for policy in policies:
            fits_pool_violation = self._fits_pool_violation_subquery(
                pool_id=pool_id,
                component_id=policy.component_id,
                request_id_expression=ResourceRequestSchema.id,
                preemptable_expression=col(ResourceRequestSchema.preemptable),
            )

            eligible_request_rows = session.exec(
                select(ResourceRequestSchema.id, ResourceRequestSchema.created)
                .where(
                    ResourceRequestSchema.component_id == policy.component_id
                )
                .where(
                    col(ResourceRequestSchema.status)
                    == ResourceRequestStatus.PENDING.value
                )
                .where(~exists(fits_pool_violation))
                .order_by(
                    col(ResourceRequestSchema.created),
                    col(ResourceRequestSchema.id),
                )
            ).all()

            for request_id, request_created in eligible_request_rows:
                session.add(
                    ResourcePoolQueueSchema(
                        pool_id=pool_id,
                        request_id=request_id,
                        priority=policy.priority,
                        request_created=request_created,
                    )
                )

        session.flush()

        # Reject pending requests that no longer fit in any pool after this
        # rebuild.
        component_ids = [a.component_id for a in policies]
        if component_ids:
            now = utc_now()
            session.execute(
                update(ResourceRequestSchema)
                .where(
                    col(ResourceRequestSchema.component_id).in_(component_ids)
                )
                .where(
                    col(ResourceRequestSchema.status)
                    == ResourceRequestStatus.PENDING.value
                )
                .where(
                    ~exists(
                        select(ResourcePoolQueueSchema.id).where(
                            col(ResourcePoolQueueSchema.request_id)
                            == col(ResourceRequestSchema.id)
                        )
                    )
                )
                .values(
                    status=ResourceRequestStatus.REJECTED.value,
                    status_reason=(
                        "No policy had capacity that could fit the requested "
                        "resources."
                    ),
                    updated=now,
                )
            )

    def _reject_requests_not_in_queue(
        self, session: "Session", component_id: Optional[UUID] = None
    ) -> None:
        """Reject pending requests that are in no queue.

        Such requests can exist if for example a resource pool gets deleted
        while the request was waiting in queue for only that pool.

        Args:
            session: DB session.
            component_id: Optional component ID to scope the rejection to.
        """
        query = (
            update(ResourceRequestSchema)
            .where(
                col(ResourceRequestSchema.status)
                == ResourceRequestStatus.PENDING.value
            )
            .where(
                ~exists(
                    select(ResourcePoolQueueSchema.id).where(
                        col(ResourcePoolQueueSchema.request_id)
                        == col(ResourceRequestSchema.id)
                    )
                )
            )
        )
        if component_id is not None:
            query = query.where(
                col(ResourceRequestSchema.component_id) == component_id
            )

        session.execute(
            query.values(
                status=ResourceRequestStatus.REJECTED.value,
                status_reason=(
                    "Request is no longer eligible for any resource pool."
                ),
                updated=utc_now(),
            )
        )

    def _acquire_resource_pool_lock(
        self,
        session: "Session",
        pool_id: UUID,
    ) -> bool:
        """Acquire a row lock on a resource pool.

        This is used to ensure a consistent lock order across allocation and
        release paths and to serialize allocators per pool.

        Args:
            session: DB session.
            pool_id: ID of the pool to lock.

        Returns:
            True if the lock was acquired, False otherwise.
        """
        if session.get_bind().dialect.name != "mysql":
            return True

        locked_pool_id = session.exec(
            select(ResourcePoolSchema.id)
            .where(col(ResourcePoolSchema.id) == pool_id)
            .with_for_update()
        ).first()

        return locked_pool_id is not None

    def _cancel_orphaned_resource_requests_for_pool(
        self, session: "Session", pool_id: UUID
    ) -> int:
        """Cancel orphaned requests that are queued/allocated in a pool.

        Args:
            session: DB session.
            pool_id: The pool for which to clean up orphaned requests.

        Returns:
            Number of orphaned requests cancelled.
        """
        requests = session.exec(
            select(ResourceRequestSchema)
            .where(col(ResourceRequestSchema.step_run_id).is_(None))
            .where(
                col(ResourceRequestSchema.status).in_(
                    [
                        ResourceRequestStatus.PENDING.value,
                        ResourceRequestStatus.ALLOCATED.value,
                        ResourceRequestStatus.PREEMPTING.value,
                    ]
                )
            )
            .where(
                or_(
                    exists(
                        select(ResourcePoolQueueSchema.id).where(
                            col(ResourcePoolQueueSchema.pool_id) == pool_id,
                            col(ResourcePoolQueueSchema.request_id)
                            == col(ResourceRequestSchema.id),
                        )
                    ),
                    exists(
                        select(ResourcePoolAllocationSchema.id).where(
                            col(ResourcePoolAllocationSchema.pool_id)
                            == pool_id,
                            col(ResourcePoolAllocationSchema.request_id)
                            == col(ResourceRequestSchema.id),
                            col(ResourcePoolAllocationSchema.released_at).is_(
                                None
                            ),
                        )
                    ),
                )
            )
        ).all()
        if not requests:
            return 0
        now = utc_now()
        for request in requests:
            # Remove the request from all queues it is in.
            session.execute(
                delete(ResourcePoolQueueSchema).where(
                    col(ResourcePoolQueueSchema.request_id) == request.id
                )
            )

            if request.status in {
                ResourceRequestStatus.ALLOCATED.value,
                ResourceRequestStatus.PREEMPTING.value,
            }:
                self._release_request_resources(
                    session=session, resource_request=request
                )

            self._set_resource_request_status(
                session=session,
                resource_request=request,
                status=ResourceRequestStatus.CANCELLED,
                status_reason=(
                    "Cancelled because owning step run no longer exists."
                ),
                updated=now,
            )

        session.flush()
        return len(requests)

    def _allocate_queued_requests_for_pool(
        self, session: "Session", pool_id: UUID, max_allocations: int = 100
    ) -> int:
        """Allocate as many queued requests for a pool as possible.

        Args:
            session: DB session.
            pool_id: ID of the pool whose queue should be processed.
            max_allocations: Maximum number of allocations to perform.

        Returns:
            Number of requests allocated in this invocation.

        # noqa: DAR401
        """
        used_by_component_key_subquery = (
            select(
                col(ResourceRequestSchema.component_id).label("component_id"),
                col(ResourceRequestResourceSchema.key).label("key"),
                func.sum(ResourceRequestResourceSchema.amount).label("used"),
            )
            .select_from(ResourcePoolAllocationSchema)
            .join(
                ResourceRequestSchema,
                col(ResourceRequestSchema.id)
                == col(ResourcePoolAllocationSchema.request_id),
            )
            .join(
                ResourceRequestResourceSchema,
                and_(
                    col(ResourceRequestResourceSchema.request_id)
                    == col(ResourceRequestSchema.id),
                ),
            )
            .where(col(ResourcePoolAllocationSchema.pool_id) == pool_id)
            .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
            .group_by(
                col(ResourceRequestSchema.component_id),
                col(ResourceRequestResourceSchema.key),
            )
        ).subquery()

        def _peek_head_queue_item(
            now: datetime,
            *,
            exclude_queue_item_ids: Set[UUID],
        ) -> Optional[ResourcePoolQueueSchema]:
            # "Dedicated-first" ordering: prefer requests that can be satisfied
            # fully from the component's currently unused reserved share.
            #
            # For each requested key, compute free_reserved = max(reserved - used, 0)
            # and require requested_amount <= free_reserved.
            reserved_free_expr = case(
                (
                    func.coalesce(
                        col(ResourcePoolSubjectPolicyResourceSchema.reserved),
                        0,
                    )
                    > func.coalesce(
                        col(used_by_component_key_subquery.c.used), 0
                    ),
                    func.coalesce(
                        col(ResourcePoolSubjectPolicyResourceSchema.reserved),
                        0,
                    )
                    - func.coalesce(
                        col(used_by_component_key_subquery.c.used), 0
                    ),
                ),
                else_=0,
            )
            reserved_fit_violation_exists = exists(
                select(1)
                .select_from(ResourceRequestResourceSchema)
                .join(
                    ResourceRequestSchema,
                    col(ResourceRequestSchema.id)
                    == col(ResourceRequestResourceSchema.request_id),
                )
                .outerjoin(
                    ResourcePoolSubjectPolicySchema,
                    and_(
                        col(ResourcePoolSubjectPolicySchema.pool_id)
                        == pool_id,
                        col(ResourcePoolSubjectPolicySchema.component_id)
                        == col(ResourceRequestSchema.component_id),
                    ),
                )
                .outerjoin(
                    ResourcePoolSubjectPolicyResourceSchema,
                    and_(
                        col(ResourcePoolSubjectPolicyResourceSchema.policy_id)
                        == col(ResourcePoolSubjectPolicySchema.id),
                        col(ResourcePoolSubjectPolicyResourceSchema.key)
                        == col(ResourceRequestResourceSchema.key),
                    ),
                )
                .outerjoin(
                    used_by_component_key_subquery,
                    and_(
                        col(used_by_component_key_subquery.c.component_id)
                        == col(ResourceRequestSchema.component_id),
                        col(used_by_component_key_subquery.c.key)
                        == col(ResourceRequestResourceSchema.key),
                    ),
                )
                .where(
                    col(ResourceRequestResourceSchema.request_id)
                    == col(ResourcePoolQueueSchema.request_id),
                    col(ResourceRequestResourceSchema.amount)
                    > reserved_free_expr,
                )
            )
            fits_fully_in_free_reserved_expr = case(
                (~reserved_fit_violation_exists, 1),
                else_=0,
            )

            # Exclude queue items that would exceed the component policy limit.
            # These are temporarily ineligible (until other requests release
            # resources), so we must not let them block the pool queue head.
            resource_key_expr = col(ResourceRequestResourceSchema.key)

            limit_violation_exists = exists(
                select(1)
                .select_from(ResourceRequestResourceSchema)
                .outerjoin(
                    ResourcePoolSubjectPolicySchema,
                    and_(
                        col(ResourcePoolSubjectPolicySchema.pool_id)
                        == pool_id,
                        col(ResourcePoolSubjectPolicySchema.component_id)
                        == col(ResourceRequestSchema.component_id),
                    ),
                )
                .outerjoin(
                    ResourcePoolSubjectPolicyResourceSchema,
                    and_(
                        col(ResourcePoolSubjectPolicyResourceSchema.policy_id)
                        == col(ResourcePoolSubjectPolicySchema.id),
                        col(ResourcePoolSubjectPolicyResourceSchema.key)
                        == col(ResourceRequestResourceSchema.key),
                    ),
                )
                .outerjoin(
                    ResourcePoolResourceSchema,
                    and_(
                        col(ResourcePoolResourceSchema.pool_id) == pool_id,
                        col(ResourcePoolResourceSchema.key)
                        == col(ResourceRequestResourceSchema.key),
                    ),
                )
                .outerjoin(
                    used_by_component_key_subquery,
                    and_(
                        col(used_by_component_key_subquery.c.component_id)
                        == col(ResourceRequestSchema.component_id),
                        col(used_by_component_key_subquery.c.key)
                        == col(ResourceRequestResourceSchema.key),
                    ),
                )
                .where(
                    col(ResourceRequestResourceSchema.request_id)
                    == col(ResourcePoolQueueSchema.request_id),
                    col(ResourceRequestResourceSchema.amount) > 0,
                )
                .where(
                    (
                        func.coalesce(
                            col(used_by_component_key_subquery.c.used), 0
                        )
                        + col(ResourceRequestResourceSchema.amount)
                    )
                    > self._effective_policy_limit_expression(
                        resource_key_expression=resource_key_expr,
                    )
                )
            )
            return session.exec(
                select(ResourcePoolQueueSchema)
                .join(
                    ResourceRequestSchema,
                    col(ResourceRequestSchema.id)
                    == col(ResourcePoolQueueSchema.request_id),
                )
                .where(col(ResourcePoolQueueSchema.pool_id) == pool_id)
                .where(
                    col(ResourcePoolQueueSchema.id).not_in(
                        exclude_queue_item_ids
                    )
                    if exclude_queue_item_ids
                    else True
                )
                .where(
                    col(ResourceRequestSchema.status)
                    == ResourceRequestStatus.PENDING.value
                )
                .where(
                    or_(
                        col(ResourcePoolQueueSchema.claim_expires_at).is_(
                            None
                        ),
                        col(ResourcePoolQueueSchema.claim_expires_at) < now,
                    )
                )
                .where(~limit_violation_exists)
                .order_by(
                    desc(fits_fully_in_free_reserved_expr),
                    desc(ResourcePoolQueueSchema.priority),
                    col(ResourcePoolQueueSchema.request_created),
                    col(ResourcePoolQueueSchema.request_id),
                )
                .limit(1)
            ).first()

        class _AllocationFailed(Exception):
            pass

        class _PolicyLimitReached(Exception):
            pass

        class _NonPreemptableReservedShareUnavailable(Exception):
            pass

        # Prevent priority inversion / "parked claims": if multiple allocators
        # run concurrently for the same pool, one can claim a high-priority item
        # while another claims and allocates a lower-priority item that is
        # temporarily the highest *visible* (unclaimed) queue entry.
        #
        if not self._acquire_resource_pool_lock(session, pool_id=pool_id):
            return 0
        self._cancel_orphaned_resource_requests_for_pool(
            session=session, pool_id=pool_id
        )
        allocations_done = 0
        skipped_due_to_temporary_ineligibility: Set[UUID] = set()
        while allocations_done < max_allocations:
            now = utc_now()
            head = _peek_head_queue_item(
                now=now,
                exclude_queue_item_ids=skipped_due_to_temporary_ineligibility,
            )
            if head is None:
                return allocations_done
            logger.debug(
                "Pool %s: considering queue item %s for request %s (prio=%s).",
                pool_id,
                head.id,
                head.request_id,
                head.priority,
            )
            requested_resources_for_head: Optional[Dict[str, int]] = None
            claim_token: Optional[UUID] = None

            try:
                with session.begin_nested():
                    claim_token = uuid4()
                    claim_expires_at = now + timedelta(seconds=30)
                    result = session.execute(
                        update(ResourcePoolQueueSchema)
                        .where(
                            col(ResourcePoolQueueSchema.id) == head.id,
                            or_(
                                col(
                                    ResourcePoolQueueSchema.claim_expires_at
                                ).is_(None),
                                col(ResourcePoolQueueSchema.claim_expires_at)
                                < now,
                            ),
                            col(ResourcePoolQueueSchema.pool_id) == pool_id,
                        )
                        .values(
                            claim_token=claim_token,
                            claim_expires_at=claim_expires_at,
                            updated=now,
                        )
                    )
                    if result.rowcount != 1:  # type: ignore[attr-defined]
                        # Another allocator won the claim.
                        logger.debug(
                            "Pool %s: failed to claim queue item %s for request %s.",
                            pool_id,
                            head.id,
                            head.request_id,
                        )
                        # Stop here to avoid allocating a lower-priority request
                        # while a higher-priority one is being processed by the
                        # allocator that won the claim.
                        return allocations_done
                    logger.debug(
                        "Pool %s: claimed queue item %s for request %s (token=%s).",
                        pool_id,
                        head.id,
                        head.request_id,
                        claim_token,
                    )

                    requested_resource_rows = session.exec(
                        select(
                            ResourceRequestResourceSchema.key,
                            ResourceRequestResourceSchema.amount,
                        ).where(
                            ResourceRequestResourceSchema.request_id
                            == head.request_id
                        )
                    ).all()

                    requested_resources = [
                        (key, amount)
                        for key, amount in requested_resource_rows
                        if amount
                    ]
                    requested_resources_for_head = {
                        key: amount for key, amount in requested_resources
                    }

                    component_id, request_preemptable = session.exec(
                        select(
                            ResourceRequestSchema.component_id,
                            ResourceRequestSchema.preemptable,
                        ).where(
                            col(ResourceRequestSchema.id) == head.request_id
                        )
                    ).one()

                    # Serialize allocations per (pool, component) so enforcing
                    # per-policy limits remains correct under concurrency.
                    logger.debug(
                        "Pool %s: acquiring policy lock for component %s.",
                        pool_id,
                        component_id,
                    )
                    session.exec(
                        select(ResourcePoolSubjectPolicySchema.id)
                        .where(
                            col(ResourcePoolSubjectPolicySchema.pool_id)
                            == pool_id,
                            col(ResourcePoolSubjectPolicySchema.component_id)
                            == component_id,
                        )
                        .with_for_update()
                    ).first()
                    logger.debug(
                        "Pool %s: acquired policy lock for component %s.",
                        pool_id,
                        component_id,
                    )

                    policy_resource_rows = session.exec(
                        select(  # type: ignore[call-overload]
                            ResourceRequestResourceSchema.key,
                            func.coalesce(
                                ResourcePoolSubjectPolicyResourceSchema.reserved,
                                0,
                            ).label("reserved"),
                            col(ResourcePoolResourceSchema.id).label(
                                "pool_resource_id"
                            ),
                            self._effective_pool_total_expression(
                                resource_key_expression=col(
                                    ResourceRequestResourceSchema.key
                                )
                            ).label("effective_pool_total"),
                            self._effective_policy_limit_expression(
                                resource_key_expression=col(
                                    ResourceRequestResourceSchema.key
                                )
                            ).label("effective_limit"),
                        )
                        .select_from(ResourceRequestResourceSchema)
                        .outerjoin(
                            ResourcePoolSubjectPolicySchema,
                            and_(
                                col(ResourcePoolSubjectPolicySchema.pool_id)
                                == pool_id,
                                col(
                                    ResourcePoolSubjectPolicySchema.component_id
                                )
                                == component_id,
                            ),
                        )
                        .outerjoin(
                            ResourcePoolSubjectPolicyResourceSchema,
                            and_(
                                col(
                                    ResourcePoolSubjectPolicyResourceSchema.policy_id
                                )
                                == col(ResourcePoolSubjectPolicySchema.id),
                                col(
                                    ResourcePoolSubjectPolicyResourceSchema.key
                                )
                                == col(ResourceRequestResourceSchema.key),
                            ),
                        )
                        .outerjoin(
                            ResourcePoolResourceSchema,
                            and_(
                                col(ResourcePoolResourceSchema.pool_id)
                                == pool_id,
                                col(ResourcePoolResourceSchema.key)
                                == col(ResourceRequestResourceSchema.key),
                            ),
                        )
                        .where(
                            col(ResourceRequestResourceSchema.request_id)
                            == head.request_id,
                            col(ResourceRequestResourceSchema.amount) > 0,
                        )
                    ).all()
                    reserved_by_key: Dict[str, int] = {}
                    effective_limit_by_key: Dict[str, int] = {}
                    effective_pool_total_by_key: Dict[str, int] = {}
                    has_explicit_pool_resource_by_key: Dict[str, bool] = {}
                    for (
                        k,
                        min,
                        pool_resource_id,
                        pool_total,
                        max,
                    ) in policy_resource_rows:
                        reserved_by_key[k] = int(min)
                        has_explicit_pool_resource_by_key[k] = (
                            pool_resource_id is not None
                        )
                        effective_pool_total_by_key[k] = int(pool_total)
                        effective_limit_by_key[k] = int(max)

                    for resource_key, amount in requested_resources:
                        if amount > effective_limit_by_key.get(
                            resource_key, 0
                        ):
                            session.execute(
                                delete(ResourcePoolQueueSchema).where(
                                    col(ResourcePoolQueueSchema.id) == head.id
                                )
                            )
                            session.flush()
                            raise _AllocationFailed()

                    used_rows = session.exec(
                        select(
                            col(ResourceRequestResourceSchema.key),
                            func.sum(
                                col(ResourceRequestResourceSchema.amount)
                            ),
                        )
                        .select_from(ResourcePoolAllocationSchema)
                        .join(
                            ResourceRequestSchema,
                            col(ResourceRequestSchema.id)
                            == col(ResourcePoolAllocationSchema.request_id),
                        )
                        .join(
                            ResourceRequestResourceSchema,
                            and_(
                                col(ResourceRequestResourceSchema.request_id)
                                == col(ResourceRequestSchema.id),
                                col(ResourceRequestResourceSchema.key).in_(
                                    list(requested_resources_for_head.keys())
                                ),
                                col(ResourceRequestResourceSchema.amount) > 0,
                            ),
                        )
                        .where(
                            col(ResourcePoolAllocationSchema.pool_id)
                            == pool_id
                        )
                        .where(
                            col(ResourcePoolAllocationSchema.released_at).is_(
                                None
                            )
                        )
                        .where(
                            col(ResourceRequestSchema.component_id)
                            == component_id
                        )
                        .group_by(col(ResourceRequestResourceSchema.key))
                    ).all()
                    used_by_key = {
                        str(key): int(used or 0) for key, used in used_rows
                    }
                    for resource_key, amount in requested_resources:
                        used = used_by_key.get(str(resource_key), 0)
                        effective_max = effective_limit_by_key.get(
                            str(resource_key), 0
                        )
                        if used + int(amount) > int(effective_max):
                            logger.debug(
                                "Pool %s: policy limit reached for component %s "
                                "key=%s used=%s req=%s max=%s (request=%s).",
                                pool_id,
                                component_id,
                                resource_key,
                                used,
                                amount,
                                effective_max,
                                head.request_id,
                            )
                            raise _PolicyLimitReached()

                    if not request_preemptable:
                        used_non_preemptable_rows = session.exec(
                            select(
                                col(ResourceRequestResourceSchema.key),
                                func.sum(
                                    col(ResourceRequestResourceSchema.amount)
                                ),
                            )
                            .select_from(ResourcePoolAllocationSchema)
                            .join(
                                ResourceRequestSchema,
                                col(ResourceRequestSchema.id)
                                == col(
                                    ResourcePoolAllocationSchema.request_id
                                ),
                            )
                            .join(
                                ResourceRequestResourceSchema,
                                and_(
                                    col(
                                        ResourceRequestResourceSchema.request_id
                                    )
                                    == col(ResourceRequestSchema.id),
                                    col(ResourceRequestResourceSchema.key).in_(
                                        list(
                                            requested_resources_for_head.keys()
                                        )
                                    ),
                                    col(ResourceRequestResourceSchema.amount)
                                    > 0,
                                ),
                            )
                            .where(
                                col(ResourcePoolAllocationSchema.pool_id)
                                == pool_id
                            )
                            .where(
                                col(
                                    ResourcePoolAllocationSchema.released_at
                                ).is_(None)
                            )
                            .where(
                                col(ResourceRequestSchema.component_id)
                                == component_id
                            )
                            .where(
                                col(ResourceRequestSchema.preemptable).is_(
                                    False
                                )
                            )
                            .group_by(col(ResourceRequestResourceSchema.key))
                        ).all()
                        used_non_preemptable_by_key = {
                            str(key): int(used or 0)
                            for key, used in used_non_preemptable_rows
                        }
                        for resource_key, amount in requested_resources:
                            used_non_preemptable = (
                                used_non_preemptable_by_key.get(
                                    resource_key, 0
                                )
                            )
                            effective_reserved = reserved_by_key.get(
                                resource_key, 0
                            )
                            if (
                                used_non_preemptable + amount
                                > effective_reserved
                            ):
                                logger.debug(
                                    "Pool %s: reserved share unavailable for "
                                    "non-preemptable request %s key=%s "
                                    "used_non_preemptable=%s requested=%s "
                                    "reserved=%s.",
                                    pool_id,
                                    head.request_id,
                                    resource_key,
                                    used_non_preemptable,
                                    amount,
                                    effective_reserved,
                                )
                                raise _NonPreemptableReservedShareUnavailable()

                    for resource_key, amount in requested_resources:
                        logger.debug(
                            "Pool %s: incrementing occupied for key=%s by %s (request=%s).",
                            pool_id,
                            resource_key,
                            amount,
                            head.request_id,
                        )
                        result = session.execute(
                            update(ResourcePoolResourceSchema)
                            .where(
                                col(ResourcePoolResourceSchema.pool_id)
                                == pool_id,
                                col(ResourcePoolResourceSchema.key)
                                == resource_key,
                                (
                                    col(ResourcePoolResourceSchema.total)
                                    - col(ResourcePoolResourceSchema.occupied)
                                )
                                >= amount,
                            )
                            .values(
                                occupied=ResourcePoolResourceSchema.occupied
                                + amount,
                                updated=now,
                            )
                        )
                        if result.rowcount != 1:  # type: ignore[attr-defined]
                            is_unbounded_missing_row = (
                                resource_key in RESOURCE_POOL_UNBOUNDED_KEYS
                                and not has_explicit_pool_resource_by_key.get(
                                    resource_key, False
                                )
                                and effective_pool_total_by_key.get(
                                    resource_key, 0
                                )
                                >= RESOURCE_POOL_UNBOUNDED_CAPACITY
                            )
                            # rowcount==0 can be legitimate only when the key
                            # has no explicit pool row and defaults to
                            # unbounded capacity. Any other zero-row update
                            # indicates a failed invariant and must fail.
                            if not is_unbounded_missing_row:
                                raise _AllocationFailed()

                    session.add(
                        ResourcePoolAllocationSchema(
                            pool_id=pool_id,
                            request_id=head.request_id,
                            allocated_at=now,
                            released_at=None,
                        )
                    )
                    # Surface allocation conflicts early (a request can only have
                    # one active allocation across all pools).
                    session.flush()

                    did_transition = (
                        self._attempt_resource_request_status_transition(
                            session=session,
                            request_id=head.request_id,
                            new_status=ResourceRequestStatus.ALLOCATED,
                            expected_status=ResourceRequestStatus.PENDING,
                            updated=now,
                        )
                    )
                    if not did_transition:
                        raise _AllocationFailed()

                    # Only remove the claimed entry from this pool queue.
                    #
                    # A request can be enqueued in multiple pools. Removing it
                    # from all pool queues here can block on locks held by other
                    # allocators that are concurrently claiming those rows,
                    # causing the allocation transaction to hold locks on pool
                    # resources while waiting. Other pools ignore non-PENDING
                    # requests anyway (and will prune stale items defensively),
                    # so removing the current row is sufficient.
                    session.execute(
                        delete(ResourcePoolQueueSchema).where(
                            col(ResourcePoolQueueSchema.id) == head.id,
                            col(ResourcePoolQueueSchema.pool_id) == pool_id,
                            col(ResourcePoolQueueSchema.claim_token)
                            == claim_token,
                        )
                    )
                    logger.debug(
                        "Pool %s: removed claimed queue item %s for request %s.",
                        pool_id,
                        head.id,
                        head.request_id,
                    )
                allocations_done += 1

            except (
                _PolicyLimitReached,
                _NonPreemptableReservedShareUnavailable,
            ):
                # Release the claim lease and continue with the next eligible
                # request. This request stays queued until the temporary
                # ineligibility condition no longer applies.
                if claim_token is not None:
                    session.execute(
                        update(ResourcePoolQueueSchema)
                        .where(
                            col(ResourcePoolQueueSchema.id) == head.id,
                            col(ResourcePoolQueueSchema.claim_token)
                            == claim_token,
                        )
                        .values(
                            claim_token=None,
                            claim_expires_at=None,
                            updated=utc_now(),
                        )
                    )
                    session.flush()
                skipped_due_to_temporary_ineligibility.add(head.id)
                continue
            except (IntegrityError, _AllocationFailed):
                head_status = session.exec(
                    select(ResourceRequestSchema.status).where(
                        col(ResourceRequestSchema.id) == head.request_id
                    )
                ).first()

                if (
                    head_status is None
                    or head_status != ResourceRequestStatus.PENDING.value
                ):
                    # Delete stale non-pending requests from the queue to avoid
                    # blocking. Ths shouldn't happen as we only enqueue pending
                    # requests.
                    session.execute(
                        delete(ResourcePoolQueueSchema).where(
                            col(ResourcePoolQueueSchema.id) == head.id
                        )
                    )
                    session.flush()
                    continue

                active_allocation = session.exec(
                    select(ResourcePoolAllocationSchema.id)
                    .where(
                        col(ResourcePoolAllocationSchema.request_id)
                        == head.request_id,
                        col(ResourcePoolAllocationSchema.released_at).is_(
                            None
                        ),
                    )
                    .limit(1)
                ).first()
                if active_allocation is not None:
                    session.execute(
                        delete(ResourcePoolQueueSchema).where(
                            col(ResourcePoolQueueSchema.id) == head.id
                        )
                    )
                    session.flush()
                    continue

                # Release the claim lease (best-effort) to avoid leaving the pool
                # head blocked if the allocation couldn't proceed.
                if claim_token is not None:
                    session.execute(
                        update(ResourcePoolQueueSchema)
                        .where(
                            col(ResourcePoolQueueSchema.id) == head.id,
                            col(ResourcePoolQueueSchema.claim_token)
                            == claim_token,
                        )
                        .values(
                            claim_token=None,
                            claim_expires_at=None,
                            updated=utc_now(),
                        )
                    )
                    session.flush()

                component_id = session.exec(
                    select(ResourceRequestSchema.component_id).where(
                        col(ResourceRequestSchema.id) == head.request_id
                    )
                ).one()

                reclaim_budget: Dict[str, int] = {}
                reclaim_budget_rows = session.exec(
                    select(
                        ResourceRequestResourceSchema.key,
                        func.coalesce(
                            col(
                                ResourcePoolSubjectPolicyResourceSchema.reserved
                            ),
                            0,
                        ).label("effective_min"),
                        func.coalesce(
                            col(used_by_component_key_subquery.c.used), 0
                        ).label("used"),
                    )
                    .select_from(ResourceRequestResourceSchema)
                    .outerjoin(
                        ResourcePoolSubjectPolicySchema,
                        and_(
                            col(ResourcePoolSubjectPolicySchema.pool_id)
                            == pool_id,
                            col(ResourcePoolSubjectPolicySchema.component_id)
                            == component_id,
                        ),
                    )
                    .outerjoin(
                        ResourcePoolSubjectPolicyResourceSchema,
                        and_(
                            col(
                                ResourcePoolSubjectPolicyResourceSchema.policy_id
                            )
                            == col(ResourcePoolSubjectPolicySchema.id),
                            col(ResourcePoolSubjectPolicyResourceSchema.key)
                            == col(ResourceRequestResourceSchema.key),
                        ),
                    )
                    .outerjoin(
                        used_by_component_key_subquery,
                        and_(
                            col(used_by_component_key_subquery.c.component_id)
                            == component_id,
                            col(used_by_component_key_subquery.c.key)
                            == col(ResourceRequestResourceSchema.key),
                        ),
                    )
                    .where(
                        col(ResourceRequestResourceSchema.request_id)
                        == head.request_id,
                        col(ResourceRequestResourceSchema.amount) > 0,
                    )
                ).all()
                for key, effective_min, used in reclaim_budget_rows:
                    budget = int(effective_min) - int(used)
                    if budget > 0:
                        reclaim_budget[str(key)] = budget

                if self._attempt_preemption_for_resource_request(
                    session=session,
                    pool_id=pool_id,
                    request_id=head.request_id,
                    priority=head.priority,
                    requested_resources=requested_resources_for_head,
                    reclaim_budget=reclaim_budget,
                ):
                    # Eviction is asynchronous; a later resource release is
                    # expected to trigger another allocation attempt.
                    return allocations_done

                # We couldn't free resources for the head request -> We stop and
                # don't continue with the next requests in the queue.
                return allocations_done

        return allocations_done

    def _release_step_run_resources(
        self, session: "Session", step_run_id: UUID
    ) -> None:
        """Release potentially acquired resources for a step run.

        Args:
            session: DB session.
            step_run_id: The ID of the step run to release resources for.
        """
        logger.debug("Releasing resources for step run `%s`", step_run_id)
        resource_requests = session.exec(
            select(ResourceRequestSchema).where(
                ResourceRequestSchema.step_run_id == step_run_id
            )
        ).all()
        freed_pool_ids: Set[UUID] = set()
        for resource_request in resource_requests:
            pool_id = self._release_request_resources(
                session, resource_request
            )
            if pool_id is not None:
                freed_pool_ids.add(pool_id)
        session.commit()

        # Trigger allocation attempts in separate transactions to avoid holding
        # locks from the release operation while claiming/allocating.
        for pool_id in freed_pool_ids:
            with Session(self.store.engine) as allocation_session:
                self._allocate_queued_requests_for_pool(
                    session=allocation_session, pool_id=pool_id
                )
                allocation_session.commit()

    def _release_request_resources(
        self, session: "Session", resource_request: ResourceRequestSchema
    ) -> Optional[UUID]:
        """Release occupied resources for a request.

        Args:
            session: DB session.
            resource_request: The resource request to release resources for.

        Returns:
            The ID of the pool for which resources were freed.
        """
        logger.debug(
            "Freeing occupied resources for request `%s`", resource_request.id
        )
        allocation = session.exec(
            select(ResourcePoolAllocationSchema).where(
                ResourcePoolAllocationSchema.request_id == resource_request.id,
                col(ResourcePoolAllocationSchema.released_at).is_(None),
            )
        ).first()
        if allocation is None:
            logger.debug(
                "Resource request `%s` has no active allocation, skipping.",
                resource_request.id,
            )
            return None

        requested_resource_rows = session.exec(
            select(
                ResourceRequestResourceSchema.key,
                ResourceRequestResourceSchema.amount,
            ).where(
                ResourceRequestResourceSchema.request_id == resource_request.id
            )
        ).all()

        now = utc_now()
        with session.begin_nested():
            self._acquire_resource_pool_lock(
                session, pool_id=allocation.pool_id
            )
            explicit_pool_resource_keys = {
                key
                for key in session.exec(
                    select(ResourcePoolResourceSchema.key).where(
                        col(ResourcePoolResourceSchema.pool_id)
                        == allocation.pool_id,
                        col(ResourcePoolResourceSchema.key).in_(
                            [
                                k
                                for k, amount in requested_resource_rows
                                if amount
                            ]
                        ),
                    )
                ).all()
            }

            for resource_key, amount in requested_resource_rows:
                if not amount:
                    continue
                logger.debug(
                    "Pool %s: decrementing occupied for key=%s by %s (request=%s).",
                    allocation.pool_id,
                    resource_key,
                    amount,
                    resource_request.id,
                )
                result = session.execute(
                    update(ResourcePoolResourceSchema)
                    .where(
                        col(ResourcePoolResourceSchema.pool_id)
                        == allocation.pool_id,
                        col(ResourcePoolResourceSchema.key) == resource_key,
                        col(ResourcePoolResourceSchema.occupied) >= amount,
                    )
                    .values(
                        occupied=ResourcePoolResourceSchema.occupied - amount,
                        updated=now,
                    )
                )
                if result.rowcount != 1:  # type: ignore[attr-defined]
                    if (
                        resource_key in RESOURCE_POOL_UNBOUNDED_KEYS
                        and resource_key not in explicit_pool_resource_keys
                    ):
                        # No explicit pool row for an unbounded default key:
                        # we never incremented occupied in DB for this key, so
                        # there is nothing to decrement now.
                        continue
                    logger.debug(
                        "Failed to decrement occupied resource `%s` of request "
                        "`%s` for pool `%s`.",
                        resource_key,
                        resource_request.id,
                        allocation.pool_id,
                    )

            allocation.released_at = now
            allocation.updated = now
            new_request_status = (
                ResourceRequestStatus.PREEMPTED
                if resource_request.status
                == ResourceRequestStatus.PREEMPTING.value
                else ResourceRequestStatus.RELEASED
            )
            self._set_resource_request_status(
                session=session,
                resource_request=resource_request,
                status=new_request_status,
                updated=now,
            )
            session.add(allocation)

        return allocation.pool_id

    def _repair_pool_occupied_resources(
        self, session: "Session", pool_id: UUID
    ) -> int:
        """Repair occupied counters for all explicit pool resource rows.

        Args:
            session: DB session.
            pool_id: The pool ID.

        Returns:
            Number of pool resource rows repaired.
        """
        occupied_by_key = {
            str(key): int(occupied or 0)
            for key, occupied in session.exec(
                select(
                    col(ResourceRequestResourceSchema.key),
                    func.sum(col(ResourceRequestResourceSchema.amount)),
                )
                .select_from(ResourcePoolAllocationSchema)
                .join(
                    ResourceRequestResourceSchema,
                    col(ResourceRequestResourceSchema.request_id)
                    == col(ResourcePoolAllocationSchema.request_id),
                )
                .where(col(ResourcePoolAllocationSchema.pool_id) == pool_id)
                .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
                .group_by(col(ResourceRequestResourceSchema.key))
            ).all()
        }

        now = utc_now()
        pool_resources = session.exec(
            select(ResourcePoolResourceSchema).where(
                col(ResourcePoolResourceSchema.pool_id) == pool_id
            )
        ).all()
        repaired_rows = 0
        for pool_resource in pool_resources:
            expected_occupied = occupied_by_key.get(pool_resource.key, 0)
            if pool_resource.occupied != expected_occupied:
                pool_resource.occupied = expected_occupied
                pool_resource.updated = now
                session.add(pool_resource)
                repaired_rows += 1

        session.flush()
        return repaired_rows

    def _prune_stale_queue_entries_for_pool(
        self, session: "Session", pool_id: UUID
    ) -> int:
        """Remove stale queue entries for non-pending requests in a pool.

        Args:
            session: DB session.
            pool_id: ID of the pool whose queue should be pruned.

        Returns:
            Number of queue entries removed.
        """
        result = session.execute(
            delete(ResourcePoolQueueSchema)
            .where(col(ResourcePoolQueueSchema.pool_id) == pool_id)
            .where(
                exists(
                    select(ResourceRequestSchema.id).where(
                        col(ResourceRequestSchema.id)
                        == col(ResourcePoolQueueSchema.request_id),
                        col(ResourceRequestSchema.status)
                        != ResourceRequestStatus.PENDING.value,
                    )
                )
            )
        )
        removed = int(result.rowcount or 0)  # type: ignore[attr-defined]
        session.flush()
        return removed

    def _reconcile_resource_pool(
        self,
        session: "Session",
        pool_id: UUID,
        *,
        max_allocations_per_pool: int = 100,
    ) -> None:
        """Run one reconciliation pass for a single pool.

        Args:
            session: DB session.
            pool_id: The pool ID.
            max_allocations_per_pool: Maximum allocations to perform.

        The pass runs orphan cancellation, occupied counter repair, queue
        rebuild and allocation in that order and logs action counters.
        """
        if not self._acquire_resource_pool_lock(session, pool_id=pool_id):
            return

        cancelled_requests = self._cancel_orphaned_resource_requests_for_pool(
            session=session, pool_id=pool_id
        )
        repaired_rows = self._repair_pool_occupied_resources(
            session=session, pool_id=pool_id
        )
        stale_queue_entries_removed = self._prune_stale_queue_entries_for_pool(
            session=session, pool_id=pool_id
        )
        self._rebuild_resource_pool_request_queue(
            session=session, pool_id=pool_id
        )
        allocations_made = self._allocate_queued_requests_for_pool(
            session=session,
            pool_id=pool_id,
            max_allocations=max_allocations_per_pool,
        )
        logger.info(
            "Resource pool `%s` reconciliation actions: "
            "cancelled=%s repaired=%s stale_pruned=%s allocations=%s.",
            pool_id,
            cancelled_requests,
            repaired_rows,
            stale_queue_entries_removed,
            allocations_made,
        )

    def reconcile_resource_pools(
        self, max_allocations_per_pool: int = 100
    ) -> None:
        """Run one full reconciliation pass for all resource pools.

        Args:
            max_allocations_per_pool: Maximum allocations to perform per pool.

        Failures are isolated per pool: one pool failure is logged and does not
        stop reconciliation for other pools.
        """
        with self.store.get_session() as session:
            pool_ids = session.exec(select(ResourcePoolSchema.id)).all()

        for pool_id in pool_ids:
            try:
                with self.store.get_session() as session:
                    self._reconcile_resource_pool(
                        session=session,
                        pool_id=pool_id,
                        max_allocations_per_pool=max_allocations_per_pool,
                    )
                    session.commit()
            except Exception:
                logger.exception(
                    "Resource pool reconciliation failed for pool `%s`.",
                    pool_id,
                )
                continue

    def _attempt_preemption_for_resource_request(
        self,
        session: "Session",
        pool_id: UUID,
        request_id: UUID,
        priority: int,
        requested_resources: Optional[Dict[str, int]],
        reclaim_budget: Dict[str, int],
    ) -> bool:
        """Attempt to free resources for the request by evicting victims.

        Args:
            session: DB session.
            pool_id: ID of the pool for which to allocate.
            request_id: ID of the blocked request.
            priority: Policy priority of the request.
            requested_resources: Optional cached requested resources for the
                head request.
            reclaim_budget: Budget that allows reclaiming borrowed
                resources even from higher-priority requests. Values represent
                the per-key shortfall of the request policy below its reserved
                share and are capped to the request deficits.

        Returns:
            True if eviction was triggered for at least one victim.
        """
        # TODO: Maybe introduce an efficiency score for picking eviction
        # victims. For example: If the second victim can fully satisfy the
        # request, but the first one can not, we do not have to evict the first
        # victim. Currently, our algorithm would evict both.
        if requested_resources is None:
            requested_resource_rows = session.exec(
                select(
                    ResourceRequestResourceSchema.key,
                    ResourceRequestResourceSchema.amount,
                ).where(ResourceRequestResourceSchema.request_id == request_id)
            ).all()
            requested_resources = {
                key: amount
                for key, amount in requested_resource_rows
                if amount
            }

        if not requested_resources:
            return False

        pool_resource_rows = session.exec(
            select(
                ResourcePoolResourceSchema.key,
                ResourcePoolResourceSchema.total,
                ResourcePoolResourceSchema.occupied,
            )
            .where(col(ResourcePoolResourceSchema.pool_id) == pool_id)
            .where(
                col(ResourcePoolResourceSchema.key).in_(
                    list(requested_resources.keys())
                )
            )
        ).all()
        pool_resources = {
            key: (total, occupied)
            for key, total, occupied in pool_resource_rows
        }

        deficits: Dict[str, int] = {}
        for key, amount in requested_resources.items():
            total_occupied = pool_resources.get(key)
            if total_occupied is None:
                if key in RESOURCE_POOL_UNBOUNDED_KEYS:
                    continue
                # This shouldn't happen for bounded keys, as requests only get
                # enqueued if the pool's total capacity is sufficient.
                return False
            total, occupied = total_occupied
            deficit = occupied + amount - total
            if deficit > 0:
                deficits[key] = deficit

        if not deficits:
            # The requested resources are already available in the pool. We
            # shouldn't be in this method at all, so we just return.
            return False

        deficit_keys = list(deficits.keys())

        # Filter the reclaim budget to only contain resources that are not
        # already available in the pool.
        reclaim_budget = {
            key: min(budget, deficits[key])
            for key, budget in reclaim_budget.items()
            if budget > 0 and key in deficits
        }

        effective_min_expr = func.coalesce(
            ResourcePoolSubjectPolicyResourceSchema.reserved, 0
        ).label("effective_min")
        cumulative_used_expr = func.sum(
            col(ResourceRequestResourceSchema.amount)
        ).over(
            partition_by=[
                col(ResourceRequestSchema.component_id),
                col(ResourceRequestResourceSchema.key),
            ],
            order_by=[
                col(ResourcePoolAllocationSchema.allocated_at),
                col(ResourcePoolAllocationSchema.request_id),
            ],
        )
        amount_expr = col(ResourceRequestResourceSchema.amount)
        prev_cumulative_used_expr = cumulative_used_expr - amount_expr
        borrowed_after_expr = case(
            (
                cumulative_used_expr > effective_min_expr,
                cumulative_used_expr - effective_min_expr,
            ),
            else_=0,
        )
        borrowed_before_expr = case(
            (
                prev_cumulative_used_expr > effective_min_expr,
                prev_cumulative_used_expr - effective_min_expr,
            ),
            else_=0,
        )
        borrowed_amount_expr = (
            borrowed_after_expr - borrowed_before_expr
        ).label("borrowed_amount")
        borrowed_any_int_expr = case(
            (borrowed_amount_expr > 0, 1),
            else_=0,
        ).label("borrowed_any_int")

        # MySQL doesn't allow mixing window functions directly inside aggregate
        # contexts (e.g. MAX(SUM(...) OVER ...)). We compute the window function
        # at row-level in a subquery and aggregate in an outer query.
        candidate_rows_subquery = (
            select(  # type: ignore[call-overload]
                ResourcePoolAllocationSchema.request_id,
                ResourcePoolAllocationSchema.allocated_at,
                ResourcePoolSubjectPolicySchema.priority,
                col(ResourceRequestResourceSchema.key).label("key"),
                amount_expr.label("amount"),
                borrowed_amount_expr,
                borrowed_any_int_expr,
            )
            .join(
                ResourceRequestSchema,
                col(ResourceRequestSchema.id)
                == col(ResourcePoolAllocationSchema.request_id),
            )
            .join(
                ResourcePoolSubjectPolicySchema,
                and_(
                    col(ResourcePoolSubjectPolicySchema.pool_id) == pool_id,
                    col(ResourcePoolSubjectPolicySchema.component_id)
                    == col(ResourceRequestSchema.component_id),
                ),
            )
            .join(
                ResourceRequestResourceSchema,
                and_(
                    col(ResourceRequestResourceSchema.request_id)
                    == col(ResourceRequestSchema.id),
                    col(ResourceRequestResourceSchema.key).in_(deficit_keys),
                    col(ResourceRequestResourceSchema.amount) > 0,
                ),
            )
            .outerjoin(
                ResourcePoolSubjectPolicyResourceSchema,
                and_(
                    col(ResourcePoolSubjectPolicyResourceSchema.policy_id)
                    == col(ResourcePoolSubjectPolicySchema.id),
                    col(ResourcePoolSubjectPolicyResourceSchema.key)
                    == col(ResourceRequestResourceSchema.key),
                ),
            )
            .where(col(ResourcePoolAllocationSchema.pool_id) == pool_id)
            .where(col(ResourcePoolAllocationSchema.released_at).is_(None))
            .where(
                col(ResourceRequestSchema.status)
                == ResourceRequestStatus.ALLOCATED.value
            )
            .where(col(ResourceRequestSchema.preemptable).is_(True))
        ).subquery()

        borrowed_any_expr = func.max(
            col(candidate_rows_subquery.c.borrowed_any_int)
        ).label("borrowed_any")

        candidate_query = (
            select(
                col(candidate_rows_subquery.c.request_id),
                col(candidate_rows_subquery.c.allocated_at),
                col(candidate_rows_subquery.c.priority),
                borrowed_any_expr,
            )
            .select_from(candidate_rows_subquery)
            .group_by(
                col(candidate_rows_subquery.c.request_id),
                col(candidate_rows_subquery.c.allocated_at),
                col(candidate_rows_subquery.c.priority),
            )
            .having(borrowed_any_expr == 1)
            .order_by(
                col(candidate_rows_subquery.c.priority),  # lowest prio first
                desc(
                    col(candidate_rows_subquery.c.allocated_at)
                ),  # shortest running first
                col(candidate_rows_subquery.c.request_id),
            )
        )

        candidate_rows = session.exec(candidate_query).all()
        if not candidate_rows:
            return False

        remaining_deficits = dict(deficits)
        remaining_reclaim_budget = dict(reclaim_budget)
        victims: List[UUID] = []
        candidates_seen: Set[UUID] = set()
        resources_by_candidate: Dict[UUID, Dict[str, int]] = {}
        borrowed_by_candidate: Dict[UUID, Dict[str, int]] = {}

        def _apply_candidate(
            candidate_id: UUID, candidate_priority: int
        ) -> bool:
            resources = resources_by_candidate.get(candidate_id, {})
            borrowed = borrowed_by_candidate.get(candidate_id, {})

            is_viable_candidate = False
            new_remaining_deficits = dict(remaining_deficits)
            for key, deficit in remaining_deficits.items():
                occupied_by_candidate = resources.get(key, 0)
                if occupied_by_candidate <= 0:
                    continue
                new_deficit = deficit - occupied_by_candidate
                if new_deficit <= 0:
                    new_remaining_deficits.pop(key, None)
                else:
                    new_remaining_deficits[key] = new_deficit
                is_viable_candidate = True

            if not is_viable_candidate:
                # The candidate doesn't actually help us reduce the deficits.
                # This could be the case if the earlier candidates already
                # reduced the deficits for all relevant resource keys that this
                # candidate is occupying.
                return False

            reclaimed_resources = False
            new_remaining_reclaim_budget = dict(remaining_reclaim_budget)
            for key, budget in remaining_reclaim_budget.items():
                reclaimed = min(borrowed.get(key, 0), budget)
                if reclaimed <= 0:
                    continue
                new_budget = budget - reclaimed
                if new_budget <= 0:
                    new_remaining_reclaim_budget.pop(key, None)
                else:
                    new_remaining_reclaim_budget[key] = new_budget
                reclaimed_resources = True

            if candidate_priority >= priority and not reclaimed_resources:
                # The request is equal/higher prio than the head request, and
                # is not borrowing any of our dedicated resources. This means
                # we cannot evict it.
                return False

            remaining_deficits.clear()
            remaining_deficits.update(new_remaining_deficits)
            remaining_reclaim_budget.clear()
            remaining_reclaim_budget.update(new_remaining_reclaim_budget)
            return True

        batch_size = 50
        for batch_start in range(0, len(candidate_rows), batch_size):
            batch = candidate_rows[batch_start : batch_start + batch_size]
            batch_ids: List[UUID] = []
            priority_by_id: Dict[UUID, int] = {}
            for candidate_id, _, candidate_priority, _ in batch:
                if candidate_id in candidates_seen:
                    continue
                candidates_seen.add(candidate_id)
                priority_by_id[candidate_id] = int(candidate_priority)
                batch_ids.append(candidate_id)

            if not batch_ids:
                continue

            batch_resource_rows = session.exec(
                select(
                    ResourceRequestResourceSchema.request_id,
                    ResourceRequestResourceSchema.key,
                    ResourceRequestResourceSchema.amount,
                )
                .where(
                    col(ResourceRequestResourceSchema.request_id).in_(
                        batch_ids
                    )
                )
                .where(
                    col(ResourceRequestResourceSchema.key).in_(deficit_keys)
                )
                .where(col(ResourceRequestResourceSchema.amount) > 0)
            ).all()
            for candidate_id, key, amount in batch_resource_rows:
                resources_by_candidate.setdefault(candidate_id, {})[key] = (
                    amount
                )

            batch_borrowed_rows = session.exec(
                select(
                    col(candidate_rows_subquery.c.request_id),
                    col(candidate_rows_subquery.c.key),
                    func.sum(col(candidate_rows_subquery.c.borrowed_amount)),
                )
                .select_from(candidate_rows_subquery)
                .where(
                    col(candidate_rows_subquery.c.request_id).in_(batch_ids)
                )
                .group_by(
                    col(candidate_rows_subquery.c.request_id),
                    col(candidate_rows_subquery.c.key),
                )
            ).all()
            for candidate_id, key, borrowed_amount in batch_borrowed_rows:
                if borrowed_amount and borrowed_amount > 0:
                    borrowed_by_candidate.setdefault(candidate_id, {})[
                        str(key)
                    ] = int(borrowed_amount)

            for candidate_id in batch_ids:
                candidate_priority = priority_by_id.get(candidate_id, 0)
                if _apply_candidate(
                    candidate_id, candidate_priority=candidate_priority
                ):
                    victims.append(candidate_id)
                if not remaining_deficits:
                    break
            if not remaining_deficits:
                break

        if remaining_deficits:
            # Even if we would evict all candidates, we would not be able
            # to free enough resources to satisfy the request.
            return False

        preempted_any = False
        for victim_id in victims:
            with session.begin_nested():
                did_transition = (
                    self._attempt_resource_request_status_transition(
                        session=session,
                        request_id=victim_id,
                        new_status=ResourceRequestStatus.PREEMPTING,
                        expected_status=ResourceRequestStatus.ALLOCATED,
                        # The head request might not be the actual request that
                        # benefits from this preemption. Because eviction is
                        # asynchronous and might take some time, other requests
                        # might jump ahead of the head request in the queue, or
                        # other allocated requests might be released that allow
                        # the head request to be allocated before the eviction
                        # finishes.
                        preemption_initiated_by_id=request_id,
                        status_reason=(
                            "Preempted to free resources for request "
                            "with higher priority."
                        ),
                        updated=utc_now(),
                    )
                )
                if not did_transition:
                    continue

                self._trigger_resource_request_eviction(
                    session=session, request_id=victim_id
                )
            preempted_any = True

        return preempted_any

    def _trigger_resource_request_eviction(
        self, session: "Session", request_id: UUID
    ) -> None:
        """Trigger the eviction of a resource request.

        Args:
            session: DB session.
            request_id: ID of the request.

        Raises:
            RuntimeError: If no step run is associated with the resource
                request.
        """
        step_run = session.exec(
            select(StepRunSchema)
            .join(
                ResourceRequestSchema,
                col(ResourceRequestSchema.step_run_id)
                == col(StepRunSchema.id),
            )
            .where(ResourceRequestSchema.id == request_id)
        ).first()
        if step_run is None:
            raise RuntimeError(
                f"Resource request `{request_id}` is not tied to a step run "
                "and can not be evicted."
            )

        if ExecutionStatus(step_run.status) not in {
            ExecutionStatus.RUNNING,
            ExecutionStatus.QUEUED,
        }:
            return

        step_run.status = ExecutionStatus.CANCELLING.value
        # TODO: add status reason
        session.add(step_run)
