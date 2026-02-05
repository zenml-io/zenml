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
"""Models representing resource requests."""

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    TypeVar,
)
from uuid import UUID

from pydantic import Field, NonNegativeInt

from zenml.enums import ResourceRequestStatus
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models import ComponentResponse, StepRunResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class ResourceRequestRequest(UserScopedRequest):
    """Request model for resource requests."""

    component_id: UUID = Field(
        title="The id of the component that is requesting the resources.",
    )
    step_run_id: Optional[UUID] = Field(
        title="The id of the step run that is requesting the resources.",
        default=None,
    )
    requested_resources: Dict[str, NonNegativeInt] = Field(
        title="The resources requested."
    )


# ------------------ Update Model ------------------


class ResourceRequestUpdate(BaseUpdate):
    """Update model for resource requests."""

    step_run_id: Optional[UUID] = Field(
        title="The id of the step run that is requesting the resources.",
        default=None,
    )


# ------------------ Response Model ------------------


class ResourceRequestResponseBody(UserScopedResponseBody):
    """Response body for resource requests."""

    status: ResourceRequestStatus = Field(
        title="The status of the resource request."
    )


class ResourceRequestResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource requests."""

    status_reason: Optional[str] = Field(
        title="The reason for the status of the resource request.",
        default=None,
    )
    requested_resources: Dict[str, int] = Field(
        title="The resources requested."
    )


class ResourceRequestResponseResources(UserScopedResponseResources):
    """Response resources for resource requests."""

    component: "ComponentResponse" = Field(
        title="The component that is requesting the resources."
    )
    step_run: Optional["StepRunResponse"] = Field(
        title="The step run that is requesting the resources.", default=None
    )


class ResourceRequestResponse(
    UserScopedResponse[
        ResourceRequestResponseBody,
        ResourceRequestResponseMetadata,
        ResourceRequestResponseResources,
    ]
):
    """Response model for resource requests."""

    def get_hydrated_version(self) -> "ResourceRequestResponse":
        """Get the hydrated version of this resource request.

        Returns:
            The hydrated version of this resource request.
        """
        from zenml.client import Client

        return Client().zen_store.get_resource_request(self.id)

    @property
    def requested_resources(self) -> Dict[str, int]:
        """The `requested_resources` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().requested_resources

    @property
    def status(self) -> ResourceRequestStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def status_reason(self) -> Optional[str]:
        """The `status_reason` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().status_reason

    @property
    def component(self) -> "ComponentResponse":
        """The `component` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().component

    @property
    def step_run(self) -> Optional["StepRunResponse"]:
        """The `step_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().step_run


# ------------------ Filter Model ------------------


class ResourceRequestFilter(UserScopedFilter):
    """Resource request filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
    ]

    component_id: Optional[UUID] = Field(
        default=None,
        description="The id of the component that is requesting the resources.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        description="The id of the step run that is requesting the resources.",
    )
    status: Optional[ResourceRequestStatus] = Field(
        default=None,
        description="The status of the resource request.",
    )
