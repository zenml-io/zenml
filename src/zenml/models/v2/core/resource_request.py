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

from datetime import datetime
from typing import (
    Any,
    Optional,
)
from uuid import UUID

from pydantic import ConfigDict, Field, PositiveInt, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import (
    ResourceRequestReclaimTolerance,
    ResourceRequestRuntimeState,
    ResourceRequestStatus,
    StackComponentType,
)
from zenml.models.v2.base.base import BaseZenModel
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)


class ResourcePoolCapacityComponentSettings(BaseZenModel):
    """Stack component settings applied when a request allocation is granted."""

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


class ResourceRequestServiceConnectorSettings(BaseZenModel):
    """Service connector settings selected for a resource request."""

    connector_id: Optional[UUID] = Field(
        default=None,
        title="The service connector ID selected for the request.",
    )
    resource_type: Optional[str] = Field(
        default=None,
        title="The service connector resource type selected for the request.",
        min_length=1,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    resource_id: Optional[str] = Field(
        default=None,
        title="The service connector resource ID selected for the request.",
        min_length=1,
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ResourcePoolQueueItem(BaseZenModel):
    """Queue item linked to a resource request."""

    id: UUID = Field(title="The unique queue item ID.")
    request_id: UUID = Field(title="The queued resource request ID.")
    pool_id: UUID = Field(title="The resource pool ID.")
    pool_name: Optional[str] = Field(
        default=None,
        title="The resource pool name.",
    )
    policy_id: UUID = Field(title="The resource policy ID.")
    priority: int = Field(title="The priority snapshot for this queue item.")
    priority_lane: bool = Field(
        default=False,
        title="Whether this queue item uses the priority lane.",
    )
    enqueued_at: datetime = Field(title="The queue insertion timestamp.")
    created: Optional[datetime] = Field(
        default=None,
        title="The queue entry creation timestamp.",
    )


class ResourcePoolAllocation(BaseZenModel):
    """Allocation grant linked to a resource request."""

    id: UUID = Field(title="The unique allocation ID.")
    request_id: UUID = Field(title="The allocated resource request ID.")
    demand_index: Optional[int] = Field(
        default=None,
        ge=0,
        title=(
            "The zero-based request demand index this grant satisfies, or "
            "None for grant-default allocations."
        ),
    )
    pool_id: UUID = Field(title="The resource pool ID.")
    pool_name: Optional[str] = Field(
        default=None,
        title="The resource pool name.",
    )
    capacity_entry_id: Optional[UUID] = Field(
        default=None,
        title="The selected resource pool capacity entry ID.",
    )
    capacity_entry_name: Optional[str] = Field(
        default=None,
        title="The selected resource pool capacity entry name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    resource_id: UUID = Field(title="The allocated resource descriptor ID.")
    resource: Optional[str] = Field(
        default=None,
        title="The allocated resource descriptor name.",
    )
    resource_kind: str = Field(
        title="The allocated resource descriptor kind.",
        min_length=1,
        max_length=STR_FIELD_MAX_LENGTH,
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
    grant_id: Optional[UUID] = Field(
        default=None,
        title="The policy grant that matched the demand, if any.",
    )
    priority: int = Field(title="The priority snapshot for this allocation.")
    priority_lane: bool = Field(
        default=False,
        title="Whether this allocation uses the priority lane.",
    )
    component_id: Optional[UUID] = Field(
        default=None,
        title="The stack component ID selected for this allocation.",
    )
    account_id: Optional[UUID] = Field(
        default=None,
        title="The external account ID selected for this allocation.",
    )
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
    created: Optional[datetime] = Field(
        default=None,
        title="The allocation creation timestamp.",
    )
    updated: Optional[datetime] = Field(
        default=None,
        title="The allocation last update timestamp.",
    )

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_subject_reference(self) -> "ResourcePoolAllocation":
        """Validate that the allocation references a subject.

        Returns:
            The validated allocation.

        Raises:
            ValueError: If neither component ID nor account ID is set.
        """
        if self.component_id is None and self.account_id is None:
            raise ValueError(
                "An allocation requires component_id or account_id."
            )
        return self


class ResourceRequestDemand(BaseZenModel):
    """Resource demand for a Resource Manager-backed request."""

    resource_id: Optional[UUID] = Field(
        default=None,
        title="The exact resource descriptor ID.",
    )
    resource: Optional[str] = Field(
        default=None,
        title="The exact resource descriptor name.",
    )
    kind: Optional[str] = Field(
        default=None,
        title="The optional resource descriptor kind.",
        min_length=1,
        max_length=64,
    )
    quantity: PositiveInt = Field(title="The resource quantity requested.")
    unit: Optional[str] = Field(
        default=None,
        title="The optional unit for the requested quantity.",
        min_length=1,
        max_length=64,
    )
    class_name: Optional[str] = Field(
        default=None,
        alias="class",
        serialization_alias="class",
        title="The exact capacity class.",
    )
    resource_selector: Optional[dict[str, Any]] = Field(
        default=None,
        title="Selector over resource descriptor fields and attributes.",
    )
    class_selector: Optional[dict[str, Any]] = Field(
        default=None,
        title="Selector over capacity class fields and attributes.",
    )

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_resource_reference(self) -> "ResourceRequestDemand":
        """Validate that the demand can resolve to a resource.

        Returns:
            The validated demand.

        Raises:
            ValueError: If no resource reference or selector is configured.
        """
        if (
            self.resource_id is None
            and self.resource is None
            and self.resource_selector is None
            and self.kind is None
        ):
            raise ValueError(
                "Resource demands require a resource ID, resource name, "
                "resource kind, or resource selector."
            )
        return self


class ResourceRequestRequest(UserScopedRequest):
    """Request model for creating resource requests."""

    component_ids: Optional[list[UUID]] = Field(
        default=None,
        title="Stack components that may satisfy the request.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The step run that is requesting the resources.",
    )
    demands: list[ResourceRequestDemand] = Field(
        min_length=1,
        title="The resource demands requested.",
    )
    pool_id: Optional[UUID] = Field(
        default=None,
        title="The exact resource pool ID.",
    )
    pool: Optional[str] = Field(
        default=None,
        title="The exact resource pool name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pool_selector: Optional[dict[str, Any]] = Field(
        default=None,
        title="Selector over pool attributes.",
    )
    preemption_group: Optional[dict[str, Any]] = Field(
        default=None,
        title="Fallback selector for protected preemption peers.",
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = Field(
        default=ResourceRequestReclaimTolerance.ANY,
        title="The capacity reclaim behavior tolerated by this request.",
    )
    lease_expires_at: Optional[datetime] = Field(
        default=None,
        title="The optional initial lease expiration timestamp.",
    )
    allocation_wait_timeout_seconds: Optional[int] = Field(
        default=None,
        title="Seconds to wait for future time-gated admission routes.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        title="Optional opaque metadata attached to the request.",
    )

    @model_validator(mode="after")
    def _validate_step_run_fields(self) -> "ResourceRequestRequest":
        """Validate step-run component and step_run_id fields.

        Returns:
            The validated resource request.

        Raises:
            ValueError: If step-run fields are inconsistent.
        """
        if self.component_ids and self.step_run_id is None:
            raise ValueError(
                "step_run_id is required when component_ids are set."
            )
        if self.step_run_id is not None and not self.component_ids:
            raise ValueError(
                "component_ids are required when step_run_id is set."
            )
        return self


class ResourceRequestRenewalRequest(BaseZenModel):
    """Request model for renewing a resource request lease."""

    lease_expires_at: datetime = Field(
        title="The renewed lease expiration timestamp.",
    )
    runtime_state: Optional[ResourceRequestRuntimeState] = Field(
        default=None,
        title="The optional owner-reported runtime state.",
    )


class ResourceRequestResponseBody(UserScopedResponseBody):
    """Response body for resource requests."""

    component_ids: list[UUID] = Field(
        default_factory=list,
        title="Stack components associated with the request.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The step run associated with the resource request.",
    )
    pipeline_run_id: Optional[UUID] = Field(
        default=None,
        title="The pipeline run associated with the resource request.",
    )
    pool_id: Optional[UUID] = Field(
        default=None,
        title="The resource pool selected for the resource request.",
    )
    step_name: Optional[str] = Field(
        default=None,
        title="The pipeline step name associated with the resource request.",
    )
    pipeline_run_name: Optional[str] = Field(
        default=None,
        title="The pipeline run name associated with the resource request.",
    )
    project_id: Optional[UUID] = Field(
        default=None,
        title="The project that owns the pipeline run for this request.",
    )
    pool_name: Optional[str] = Field(
        default=None,
        title="The resource pool name selected for the resource request.",
    )
    pool_selector: Optional[dict[str, Any]] = Field(
        default=None,
        title="Selector over pool attributes requested for the resource request.",
    )
    preemption_group: Optional[dict[str, Any]] = Field(
        default=None,
        title="The request-level fallback preemption group selector.",
    )
    demands: list[ResourceRequestDemand] = Field(
        default_factory=list,
        title="The resource demands requested.",
    )
    status: ResourceRequestStatus = Field(
        title="The status of the resource request."
    )
    runtime_state: ResourceRequestRuntimeState = Field(
        default=ResourceRequestRuntimeState.UNKNOWN,
        title="The owner-reported runtime state of the request.",
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = Field(
        title="The capacity reclaim behavior tolerated by this request.",
    )
    lease_expires_at: Optional[datetime] = Field(
        default=None,
        title="The optional lease expiration timestamp.",
    )
    allocation_deadline: Optional[datetime] = Field(
        default=None,
        title="The deadline for waiting on future time-gated admission routes.",
    )
    renewed_at: Optional[datetime] = Field(
        default=None,
        title="The optional lease renewal timestamp.",
    )
    allocated_at: Optional[datetime] = Field(
        default=None,
        title="The timestamp when capacity was first granted.",
    )
    released_at: Optional[datetime] = Field(
        default=None,
        title="The timestamp when the request was released.",
    )
    queued_at: Optional[datetime] = Field(
        default=None,
        title="The timestamp when the request first entered a pool queue.",
    )
    status_reason: Optional[str] = Field(
        title="The reason for the status of the resource request.",
        default=None,
    )
    preemption_initiated_by_id: Optional[UUID] = Field(
        default=None,
        title="The request that initiated preemption.",
    )


class ResourceRequestResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource requests."""


class ResourceRequestResponseResources(UserScopedResponseResources):
    """Response resources for resource requests."""

    component_settings: dict[str, Any] = Field(
        default_factory=dict,
        title="Stack component settings selected for this request.",
    )
    service_connector_settings: Optional[
        ResourceRequestServiceConnectorSettings
    ] = Field(
        default=None,
        title="Service connector settings selected for this request.",
    )
    allocations: list[ResourcePoolAllocation] = Field(
        default_factory=list,
        title="Allocation grants linked to this request.",
    )
    queue_entries: list[ResourcePoolQueueItem] = Field(
        default_factory=list,
        title="Pool queue memberships linked to this request.",
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
            The current resource request fetched from the configured ZenML
            store.
        """
        from zenml.client import Client

        return Client().zen_store.get_resource_request(self.id)

    @property
    def component_ids(self) -> list[UUID]:
        """Resource request component IDs.

        Returns:
            Stack components associated with the resource request.
        """
        return self.get_body().component_ids

    @property
    def step_run_id(self) -> Optional[UUID]:
        """Resource request step run ID.

        Returns:
            The optional step run associated with the resource request.
        """
        return self.get_body().step_run_id

    @property
    def pipeline_run_id(self) -> Optional[UUID]:
        """Resource request pipeline run ID.

        Returns:
            The optional pipeline run associated with the resource request.
        """
        return self.get_body().pipeline_run_id

    @property
    def pool_id(self) -> Optional[UUID]:
        """Resource request pool ID.

        Returns:
            The optional resource pool selected for the request.
        """
        return self.get_body().pool_id

    @property
    def demands(self) -> list[ResourceRequestDemand]:
        """Requested resource demands.

        Returns:
            The resource demands requested.
        """
        return self.get_body().demands

    @property
    def preemption_group(self) -> Optional[dict[str, Any]]:
        """Request-level fallback preemption group selector.

        Returns:
            The optional selector configured on the request.
        """
        return self.get_body().preemption_group

    @property
    def reclaim_tolerance(self) -> ResourceRequestReclaimTolerance:
        """Resource request reclaim tolerance.

        Returns:
            The reclaim behavior tolerated by the request.
        """
        return self.get_body().reclaim_tolerance

    @property
    def lease_expires_at(self) -> Optional[datetime]:
        """Resource request lease expiration timestamp.

        Returns:
            The optional lease expiration timestamp.
        """
        return self.get_body().lease_expires_at

    @property
    def renewed_at(self) -> Optional[datetime]:
        """Resource request renewal timestamp.

        Returns:
            The optional lease renewal timestamp.
        """
        return self.get_body().renewed_at

    @property
    def status(self) -> ResourceRequestStatus:
        """Resource request status.

        Returns:
            The lifecycle status of the resource request.
        """
        return self.get_body().status

    @property
    def runtime_state(self) -> ResourceRequestRuntimeState:
        """Resource request runtime state.

        Returns:
            The owner-reported runtime state of the resource request.
        """
        return self.get_body().runtime_state

    @property
    def status_reason(self) -> Optional[str]:
        """Resource request status reason.

        Returns:
            The optional status reason.
        """
        return self.get_body().status_reason

    @property
    def preemption_initiated_by_id(self) -> Optional[UUID]:
        """Request that initiated preemption.

        Returns:
            The optional ID of the request that initiated preemption.
        """
        return self.get_body().preemption_initiated_by_id


class ResourceRequestFilter(UserScopedFilter):
    """Resource request filter model."""

    user: UUID | str | None = Field(
        default=None,
        description="Name/ID of the user that created the entity.",
        union_mode="left_to_right",
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance | str | None = Field(
        default=None,
        description="The reclaim behavior tolerated by the request.",
        union_mode="left_to_right",
    )
    component_id: UUID | str | None = Field(
        default=None,
        description="The component requesting resources.",
        union_mode="left_to_right",
    )
    step_run_id: UUID | str | None = Field(
        default=None,
        description="The step run requesting resources.",
        union_mode="left_to_right",
    )
    preemption_initiated_by_id: UUID | str | None = Field(
        default=None,
        description="The request that initiated preemption.",
        union_mode="left_to_right",
    )
    status: ResourceRequestStatus | str | None = Field(
        default=None,
        description="The status of the resource request.",
        union_mode="left_to_right",
    )
    pipeline_run_id: UUID | str | None = Field(
        default=None,
        description="The pipeline run requesting resources.",
        union_mode="left_to_right",
    )
    pool_id: UUID | str | None = Field(
        default=None,
        description="The resource pool linked to the request.",
        union_mode="left_to_right",
    )
