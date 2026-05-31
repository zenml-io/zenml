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
from typing import Any, ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import ConfigDict, Field, NonNegativeInt, PositiveInt

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.filter import StringFilterOption
from zenml.models.v2.base.base import BaseZenModel
from zenml.enums import StackComponentType
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)
from zenml.utils.enum_utils import StrEnum


class ResourcePoolReclaimable(StrEnum):
    """How safely capacity on a resource pool class can be reclaimed."""

    NEVER = "never"
    COORDINATED = "coordinated"
    UNSAFE = "unsafe"


class ResourcePoolCapacityComponentSettings(BaseZenModel):
    """Stack component settings applied when a capacity class is allocated."""

    component_type: StackComponentType = Field(
        title="The stack component type to apply settings to.",
    )
    flavor: str = Field(
        title="The stack component flavor to apply settings to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        title="The stack component settings to apply on allocation.",
    )


class ResourcePoolCapacityClass(BaseZenModel):
    """Capacity class entry for a resource pool."""

    resource_id: Optional[UUID] = Field(
        default=None,
        title="The resource descriptor ID.",
    )
    resource: Optional[str] = Field(
        default=None,
        title="The resource descriptor name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    class_name: str = Field(
        alias="class",
        serialization_alias="class",
        title="The capacity class name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    quantity: PositiveInt = Field(title="The declared capacity quantity.")
    unit: Optional[str] = Field(
        default=None,
        title="The optional unit for the declared capacity quantity.",
        min_length=1,
        max_length=64,
    )
    rank: int = Field(title="The precedence rank for this capacity class.")
    reclaimable: ResourcePoolReclaimable = Field(
        title="The capacity reclaim behavior."
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        title="Metadata for matching and display.",
    )
    component_settings: list[ResourcePoolCapacityComponentSettings] = Field(
        default_factory=list,
        title="Stack component settings applied when this capacity class is allocated.",
    )

    model_config = ConfigDict(populate_by_name=True)


class ResourcePoolLedgerOccupied(BaseZenModel):
    """Occupied resource pool capacity entry."""

    resource_id: UUID = Field(title="The resource descriptor ID.")
    resource: Optional[str] = Field(
        default=None,
        title="The resource descriptor name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    class_name: str = Field(
        alias="class",
        serialization_alias="class",
        title="The capacity class name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    quantity: NonNegativeInt = Field(title="The occupied quantity.")

    model_config = ConfigDict(populate_by_name=True)


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
    capacity: list[ResourcePoolCapacityClass] = Field(
        title="The full capacity declaration for the resource pool.",
        min_length=1,
    )


class ResourcePoolUpdate(BaseUpdate):
    """Update model for resource pools."""

    name: Optional[str] = Field(
        title="The new resource pool name.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the resource pool",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    clear_description: bool = Field(
        default=False,
        title="Whether to clear the resource pool description.",
    )
    capacity: Optional[list[ResourcePoolCapacityClass]] = Field(
        title="The full replacement capacity declaration.",
        default=None,
    )


class ResourcePoolResponseBody(UserScopedResponseBody):
    """Response body for resource pools."""

    capacity: list[ResourcePoolCapacityClass] = Field(
        title="The full capacity declaration for the resource pool.",
    )
    occupied_resources: list[ResourcePoolLedgerOccupied] = Field(
        default_factory=list,
        title="The occupied resources of the resource pool.",
    )
    queue_length: NonNegativeInt = Field(
        default=0,
        title="The number of queued requests for the resource pool.",
    )


class ResourcePoolResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource pools."""

    description: Optional[str] = Field(
        default=None,
        title="The description of the resource pool",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ResourcePoolResponseResources(UserScopedResponseResources):
    """Response resources for resource pools."""


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
            The current resource pool fetched from the configured ZenML store.
        """
        from zenml.client import Client

        return Client().zen_store.get_resource_pool(self.id)

    @property
    def description(self) -> Optional[str]:
        """Resource pool description.

        Returns:
            The optional resource pool description.
        """
        return self.get_metadata().description

    @property
    def capacity(self) -> list[ResourcePoolCapacityClass]:
        """Resource pool capacity declaration.

        Returns:
            The resource pool capacity classes.
        """
        return self.get_body().capacity

    @property
    def occupied_resources(self) -> list[ResourcePoolLedgerOccupied]:
        """Occupied resource pool capacity.

        Returns:
            The occupied resource quantities reported by the Resource Manager.
        """
        return self.get_body().occupied_resources

    @property
    def queue_length(self) -> int:
        """Resource pool queue length.

        Returns:
            The number of queued requests reported by the Resource Manager.
        """
        return self.get_body().queue_length


class ResourcePoolQueueItem(BaseZenModel):
    """Queue item returned by explicit resource pool queue reads."""

    id: UUID = Field(title="The unique queue item ID.")
    request_id: UUID = Field(title="The queued resource request ID.")
    pool_id: UUID = Field(title="The resource pool ID.")
    policy_id: UUID = Field(title="The resource policy ID.")
    priority: int = Field(title="The priority snapshot for this queue item.")
    enqueued_at: datetime = Field(title="The queue insertion timestamp.")


class ResourcePoolAllocation(BaseZenModel):
    """Allocation returned by explicit resource pool allocation reads."""

    id: UUID = Field(title="The unique allocation ID.")
    request_id: UUID = Field(title="The allocated resource request ID.")
    pool_id: UUID = Field(title="The resource pool ID.")
    resource_id: UUID = Field(title="The allocated resource descriptor ID.")
    resource: Optional[str] = Field(
        default=None,
        title="The allocated resource descriptor name.",
    )
    class_name: str = Field(
        alias="class",
        serialization_alias="class",
        title="The allocated capacity class.",
    )
    quantity: PositiveInt = Field(title="The allocated quantity.")
    unit: Optional[str] = Field(
        default=None,
        title="The optional unit for the allocated quantity.",
        min_length=1,
        max_length=64,
    )
    base_quantity: Optional[PositiveInt] = Field(
        default=None,
        title="The allocated quantity converted to the descriptor base unit.",
    )
    policy_id: UUID = Field(title="The policy that admitted this allocation.")
    grant_id: UUID = Field(title="The policy grant that matched the demand.")
    priority: int = Field(title="The priority snapshot for this allocation.")
    component_id: UUID = Field(title="The selected stack component ID.")
    component_settings: list[ResourcePoolCapacityComponentSettings] = Field(
        default_factory=list,
        title="Stack component settings applied for this allocation.",
    )
    preemption_state: str = Field(title="The preemption state.")
    preemption_reason: Optional[str] = Field(
        default=None,
        title="The preemption reason.",
    )
    released_at: Optional[datetime] = Field(
        default=None,
        title="The release timestamp.",
    )

    model_config = ConfigDict(populate_by_name=True)


class ResourcePoolFilter(UserScopedFilter):
    """Resource pool filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
    ]

    name: StringFilterOption = Field(
        default=None,
        description="Name of the resource pool",
    )
    id: Union[UUID, str, None] = Field(
        default=None,
        description="ID of the resource pool.",
    )
