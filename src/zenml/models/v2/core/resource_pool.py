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
"""Models representing resource pools."""

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    TypeVar,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)
from zenml.models.v2.core.component import ComponentResponse

if TYPE_CHECKING:
    from zenml.models.v2.core.resource_request import ResourceRequestResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


class ResourcePoolSubjectPolicyResponse(ComponentResponse):
    """Response model for resource pool subject policies."""

    priority: int = Field(
        title="The priority of the component in the resource pool.",
    )
    reserved: Dict[str, NonNegativeInt] = Field(
        title="The resources that are reserved for the component.",
    )
    limit: Dict[str, NonNegativeInt] = Field(
        title="The maximum resources that the component can use.",
    )

    def get_hydrated_version(self) -> "ResourcePoolSubjectPolicyResponse":
        """Get the hydrated version of this resource pool subject policy.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return ResourcePoolSubjectPolicyResponse(
            priority=self.priority,
            **Client().zen_store.get_stack_component(self.id).model_dump(),
        )


class ResourcePoolAllocation(BaseModel):
    """Resource pool allocation."""

    request: "ResourceRequestResponse" = Field(
        title="The request that is allocated to the resource pool.",
    )
    priority: int = Field(
        title="The priority of the component in the resource pool.",
    )
    allocated_at: datetime = Field(
        title="The time the resource pool was allocated.",
    )
    borrowed_resources: Dict[str, int] = Field(
        title="Borrowed resources used by this allocation.",
        default_factory=dict,
    )


class ResourcePoolQueueItem(BaseModel):
    """Resource pool queue item."""

    request: "ResourceRequestResponse" = Field(
        title="The request that is queued for the resource pool.",
    )
    priority: int = Field(
        title="The priority of the request in the resource pool.",
    )


class ResourcePoolSubjectPolicyRequest(BaseModel):
    """Resource pool subject policy request."""

    component_id: UUID = Field(
        title="The ID of the component that is the subject of the policy.",
    )
    priority: NonNegativeInt = Field(
        title="The priority of the component in the resource pool. Higher "
        "means preferred.",
    )
    reserved: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The resources that are reserved for the component.",
        default=None,
    )
    limit: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The maximum resources that the component can use.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_resources(self) -> "ResourcePoolSubjectPolicyRequest":
        if not self.reserved or not self.limit:
            return self

        for key, reserved_value in self.reserved.items():
            limit_value = self.limit.get(key)

            if limit_value is not None and reserved_value > limit_value:
                raise ValueError(
                    f"Reserved value for resource `{key}` ({reserved_value}) "
                    f"must be less than limit `{limit_value}`."
                )

        return self


# ------------------ Request Model ------------------


class ResourcePoolRequest(UserScopedRequest):
    """Request model for resource pool creation."""

    name: str = Field(
        title="The name of the resource pool.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: Optional[str] = Field(
        title="The description of the resource pool",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    capacity: Dict[str, PositiveInt] = Field(
        title="The capacity of the resource pool.",
    )
    policies: Optional[List[ResourcePoolSubjectPolicyRequest]] = Field(
        title="The policies for the resource pool.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_capacity(self) -> "ResourcePoolRequest":
        if not self.capacity:
            raise ValueError(
                "Resource pools with no capacity are not allowed."
            )

        return self


# ------------------ Update Model ------------------


class ResourcePoolUpdate(BaseUpdate):
    """Update model for resource pools."""

    description: Optional[str] = Field(
        title="The description of the resource pool",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    capacity: Optional[Dict[str, NonNegativeInt]] = Field(
        title="The capacity of the resource pool.",
        description="The capacity of the resource pool. Setting a value to 0 "
        "will remove the resource from the pool.",
        default=None,
    )
    attach_policies: Optional[List[ResourcePoolSubjectPolicyRequest]] = Field(
        title="The policies to attach to the resource pool.",
        default=None,
    )
    detach_policies: Optional[List[UUID]] = Field(
        title="List of component IDs for which to detach policies from the "
        "resource pool.",
        default=None,
    )


# ------------------ Response Model ------------------


class ResourcePoolResponseBody(UserScopedResponseBody):
    """Response body for resource pools."""


class ResourcePoolResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource pools."""

    description: Optional[str] = Field(
        default="",
        title="The description of the resource pool",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    capacity: Dict[str, int] = Field(
        title="The capacity of the resource pool.",
    )
    occupied_resources: Dict[str, int] = Field(
        title="The occupied resources of the resource pool.",
    )


class ResourcePoolResponseResources(UserScopedResponseResources):
    """Response resources for resource pools."""

    policies: List["ResourcePoolSubjectPolicyResponse"] = Field(
        title="The policies assigned to the resource pool.",
    )
    active_requests: List["ResourcePoolAllocation"] = Field(
        title="The active requests for the resource pool.",
    )
    queued_requests: List["ResourcePoolQueueItem"] = Field(
        title="The queued requests for the resource pool.",
    )


class ResourcePoolResponse(
    UserScopedResponse[
        ResourcePoolResponseBody,
        ResourcePoolResponseMetadata,
        ResourcePoolResponseResources,
    ]
):
    """Response model for resource pools."""

    name: str = Field(
        title="The name of the resource pool.", max_length=STR_FIELD_MAX_LENGTH
    )

    def get_hydrated_version(self) -> "ResourcePoolResponse":
        """Get the hydrated version of this resource pool.

        Returns:
            The hydrated version of this resource pool.
        """
        from zenml.client import Client

        return Client().zen_store.get_resource_pool(self.id)

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def capacity(self) -> Dict[str, int]:
        """The `capacity` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().capacity

    @property
    def occupied_resources(self) -> Dict[str, int]:
        """The `occupied_resources` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().occupied_resources

    @property
    def policies(self) -> List["ResourcePoolSubjectPolicyResponse"]:
        """The `policies` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().policies

    @property
    def queued_requests(self) -> List["ResourcePoolQueueItem"]:
        """The `queued_requests` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().queued_requests

    @property
    def active_requests(self) -> List["ResourcePoolAllocation"]:
        """The `active_requests` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().active_requests


# ------------------ Filter Model ------------------


class ResourcePoolFilter(UserScopedFilter):
    """Resource pool filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the resource pool",
    )
