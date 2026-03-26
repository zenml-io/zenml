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
from uuid import UUID

from zenml.models import (
    Page,
    ResourcePoolFilter,
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


class ResourcePoolsStoreInterface(ABC):
    """Resource pools store interface."""

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
    def create_resource_pool_subject_policy(
        self, policy: ResourcePoolSubjectPolicyRequest
    ) -> ResourcePoolSubjectPolicyResponse:
        """Create a resource pool subject policy.

        Args:
            policy: The policy to create.

        Returns:
            The created policy.
        """

    @abstractmethod
    def get_resource_pool_subject_policy(
        self, policy_id: UUID, hydrate: bool = True
    ) -> ResourcePoolSubjectPolicyResponse:
        """Get a resource pool subject policy by ID.

        Args:
            policy_id: The ID of the policy to get.
            hydrate: Whether to include metadata fields.

        Returns:
            The requested policy.
        """

    @abstractmethod
    def list_resource_pool_subject_policies(
        self,
        filter_model: ResourcePoolSubjectPolicyFilter,
        hydrate: bool = False,
    ) -> Page[ResourcePoolSubjectPolicyResponse]:
        """List resource pool subject policies.

        Args:
            filter_model: All filter parameters including pagination params.
            hydrate: Whether to include metadata fields.

        Returns:
            Matching policies.
        """

    @abstractmethod
    def update_resource_pool_subject_policy(
        self, policy_id: UUID, update: ResourcePoolSubjectPolicyUpdate
    ) -> ResourcePoolSubjectPolicyResponse:
        """Update an existing resource pool subject policy.

        Args:
            policy_id: The ID of the policy to update.
            update: The update model.

        Returns:
            The updated policy.
        """

    @abstractmethod
    def delete_resource_pool_subject_policy(self, policy_id: UUID) -> None:
        """Delete a resource pool subject policy.

        Args:
            policy_id: The ID of the policy to delete.
        """

    # -------------------- Resource Requests -------------

    @abstractmethod
    def create_resource_request(
        self, resource_request: ResourceRequestRequest
    ) -> ResourceRequestResponse:
        """Create a resource request.

        Args:
            resource_request: The resource request to create.

        Returns:
            The created resource request.
        """

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

    @abstractmethod
    def delete_resource_request(self, resource_request_id: UUID) -> None:
        """Delete a resource request.

        Args:
            resource_request_id: The ID of the resource request to delete.
        """
