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

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    TypeVar,
)

from pydantic import Field, NonNegativeInt, PositiveInt, model_validator

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


# ------------------ Request Model ------------------


class ResourcePoolComponentResponse(ComponentResponse):
    """Response model for resource pool components."""

    priority: int = Field(
        title="The priority of the component in the resource pool.",
    )

    def get_hydrated_version(self) -> "ResourcePoolComponentResponse":
        """Get the hydrated version of this resource pool component.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return ResourcePoolComponentResponse(
            priority=self.priority,
            **Client().zen_store.get_stack_component(self.id).model_dump(),
        )


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

    components: List["ResourcePoolComponentResponse"] = Field(
        title="The components assigned to the resource pool.",
    )
    queued_requests: List["ResourceRequestResponse"] = Field(
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
    def components(self) -> List["ResourcePoolComponentResponse"]:
        """The `components` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().components

    @property
    def queued_requests(self) -> List["ResourceRequestResponse"]:
        """The `queued_requests` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().queued_requests


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
