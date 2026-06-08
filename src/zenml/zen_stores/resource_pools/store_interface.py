#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Resource pools store interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

from zenml.models import (
    Page,
    ResourceDescriptorFilter,
    ResourceDescriptorRequest,
    ResourceDescriptorResponse,
    ResourceDescriptorUpdate,
    ResourcePolicyFilter,
    ResourcePolicyRequest,
    ResourcePolicyResponse,
    ResourcePolicyUpdate,
    ResourcePoolAllocation,
    ResourcePoolFilter,
    ResourcePoolQueueItem,
    ResourcePoolRequest,
    ResourcePoolResponse,
    ResourcePoolUpdate,
    ResourceRequestFilter,
    ResourceRequestRequest,
    ResourceRequestResponse,
    ResourceRequestTerminateRequest,
)
from zenml.models.v2.core.resource_request import (
    ResourceRequestRenewalRequest,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


class ResourcePoolsStoreInterface(ABC):
    """Resource pools store interface."""

    # -------------------- Resource Descriptors -------------

    @abstractmethod
    def create_resource_descriptor(
        self, descriptor: ResourceDescriptorRequest
    ) -> ResourceDescriptorResponse:
        """Create a resource descriptor.

        Args:
            descriptor: The resource descriptor to create.

        Returns:
            The created resource descriptor.
        """

    @abstractmethod
    def get_resource_descriptor(
        self, descriptor_id: UUID
    ) -> ResourceDescriptorResponse:
        """Get a resource descriptor by ID.

        Args:
            descriptor_id: The ID of the resource descriptor to get.

        Returns:
            The resource descriptor.
        """

    @abstractmethod
    def list_resource_descriptors(
        self, filter_model: ResourceDescriptorFilter
    ) -> Page[ResourceDescriptorResponse]:
        """List resource descriptors matching the given filter criteria.

        Args:
            filter_model: Filter and pagination parameters.

        Returns:
            Matching resource descriptors.
        """

    @abstractmethod
    def update_resource_descriptor(
        self, descriptor_id: UUID, update: ResourceDescriptorUpdate
    ) -> ResourceDescriptorResponse:
        """Update an existing resource descriptor.

        Args:
            descriptor_id: The ID of the descriptor to update.
            update: The update to apply.

        Returns:
            The updated descriptor.
        """

    @abstractmethod
    def delete_resource_descriptor(self, descriptor_id: UUID) -> None:
        """Delete a resource descriptor.

        Args:
            descriptor_id: The ID of the descriptor to delete.
        """

    # -------------------- Resource Pools -------------

    @abstractmethod
    def create_resource_pool(
        self, resource_pool: ResourcePoolRequest
    ) -> ResourcePoolResponse:
        """Create a resource pool.

        Args:
            resource_pool: The resource pool to create.

        Returns:
            The created resource pool.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def delete_resource_pool(self, resource_pool_id: UUID) -> None:
        """Delete a resource pool.

        Args:
            resource_pool_id: The ID of the resource pool to delete.
        """

    @abstractmethod
    def list_resource_pool_queue(
        self, resource_pool_id: UUID
    ) -> Page[ResourcePoolQueueItem]:
        """List queued requests for a resource pool.

        Args:
            resource_pool_id: The ID of the resource pool.

        Returns:
            Queued requests for the pool.
        """

    @abstractmethod
    def list_resource_pool_allocations(
        self, resource_pool_id: UUID
    ) -> Page[ResourcePoolAllocation]:
        """List active allocations for a resource pool.

        Args:
            resource_pool_id: The ID of the resource pool.

        Returns:
            Active allocations for the pool.
        """

    @abstractmethod
    def create_resource_policy(
        self, policy: ResourcePolicyRequest
    ) -> ResourcePolicyResponse:
        """Create a resource policy.

        Args:
            policy: The policy to create.

        Returns:
            The created policy.
        """

    @abstractmethod
    def get_resource_policy(
        self, policy_id: UUID, hydrate: bool = True
    ) -> ResourcePolicyResponse:
        """Get a resource policy by ID.

        Args:
            policy_id: The ID of the policy to get.
            hydrate: Ignored for Resource Manager-backed policies.

        Returns:
            The requested policy.
        """

    @abstractmethod
    def list_resource_policies(
        self,
        filter_model: ResourcePolicyFilter,
        hydrate: bool = False,
    ) -> Page[ResourcePolicyResponse]:
        """List resource policies.

        Args:
            filter_model: All filter parameters including pagination params.
            hydrate: Ignored for Resource Manager-backed policies.

        Returns:
            Matching policies.
        """

    @abstractmethod
    def update_resource_policy(
        self, policy_id: UUID, update: ResourcePolicyUpdate
    ) -> ResourcePolicyResponse:
        """Update an existing resource policy.

        Args:
            policy_id: The ID of the policy to update.
            update: The update model.

        Returns:
            The updated policy.
        """

    @abstractmethod
    def delete_resource_policy(self, policy_id: UUID) -> None:
        """Delete a resource policy.

        Args:
            policy_id: The ID of the policy to delete.
        """

    # -------------------- Resource Requests -------------

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def terminate_resource_request(
        self,
        resource_request_id: UUID,
        terminate_request: ResourceRequestTerminateRequest,
    ) -> ResourceRequestResponse:
        """Terminate a resource request.

        Args:
            resource_request_id: The ID of the resource request to terminate.
            terminate_request: Termination options such as force and reason.

        Returns:
            The terminated resource request.
        """

    @abstractmethod
    def release_resource_request(
        self,
        resource_request_id: UUID,
    ) -> ResourceRequestResponse:
        """Release a resource request on behalf of its owner.

        Args:
            resource_request_id: The ID of the resource request to release.

        Returns:
            The released resource request.
        """

    @abstractmethod
    def renew_resource_request(
        self,
        resource_request_id: UUID,
        renewal_request: ResourceRequestRenewalRequest,
    ) -> ResourceRequestResponse:
        """Renew a resource request lease.

        Args:
            resource_request_id: The ID of the resource request to renew.
            renewal_request: The renewed lease expiration timestamp.

        Returns:
            The renewed resource request.
        """

    @abstractmethod
    def delete_resource_request(self, resource_request_id: UUID) -> None:
        """Delete a terminal resource request from persistence.

        Args:
            resource_request_id: The ID of the resource request to delete.
        """

    @abstractmethod
    def create_resource_request(
        self,
        resource_request: ResourceRequestRequest,
    ) -> ResourceRequestResponse:
        """Create a resource request.

        Args:
            resource_request: The resource request to create.

        Returns:
            The created resource request.
        """


class ResourcePoolsSQLStoreInterface(ResourcePoolsStoreInterface):
    """Resource pools SQL store interface."""

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize the resource pools SQL store.

        Args:
            store: The store to use.
        """
        super().__init__()
        self.store = store
        store.resource_pools = self

    @abstractmethod
    def create_resource_request_for_step_run(
        self,
        session: "Session",
        resource_request: ResourceRequestRequest,
    ) -> ResourceRequestResponse:
        """Create a step-run resource request with SQL session-backed metadata.

        Args:
            session: DB session used to enrich step-run metadata.
            resource_request: The resource request to create.

        Returns:
            The created resource request.
        """

    @abstractmethod
    def release_step_run_resources(
        self, session: "Session", step_run_id: UUID
    ) -> None:
        """Release potentially acquired resources for a step run.

        Args:
            session: DB session.
            step_run_id: The ID of the step run to release resources for.
        """

    @abstractmethod
    def delete_component_subject(
        self, session: "Session", component_id: UUID
    ) -> None:
        """Delete Resource Manager state associated with a stack component.

        Args:
            session: DB session.
            component_id: The ID of the stack component being deleted.
        """
