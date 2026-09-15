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
"""Resource request store interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

from zenml.models import (
    Page,
    ResourceRequestFilter,
    ResourceRequestRequest,
    ResourceRequestResponse,
)
from zenml.models.v2.core.resource_request import (
    ResourceRequestRenewalRequest,
)

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import Session, SqlZenStore


class ResourcePoolsStoreInterface(ABC):
    """Resource request store interface."""

    @abstractmethod
    def get_resource_request(
        self, resource_request_id: UUID, hydrate: bool = True
    ) -> ResourceRequestResponse:
        """Get a resource request by ID.

        Args:
            resource_request_id: The ID of the resource request to get.
            hydrate: Whether to hydrate metadata and resources.

        Returns:
            The resource request.
        """

    @abstractmethod
    def list_resource_requests(
        self, filter_model: ResourceRequestFilter, hydrate: bool = False
    ) -> Page[ResourceRequestResponse]:
        """List resource requests matching the given filter criteria.

        Args:
            filter_model: Filter and pagination parameters.
            hydrate: Whether to hydrate metadata and resources.

        Returns:
            Matching resource requests.
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


class ResourcePoolsSQLStoreInterface(ResourcePoolsStoreInterface):
    """Resource request SQL store interface."""

    def __init__(self, store: "SqlZenStore") -> None:
        """Initialize the resource request SQL store.

        Args:
            store: The store to use.
        """
        super().__init__()
        self.store = store
        store.resource_pools = self

    @abstractmethod
    def create_resource_request(
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
