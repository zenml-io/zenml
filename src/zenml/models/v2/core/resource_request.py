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
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import ConfigDict, Field, PositiveInt, model_validator

from zenml.models.v2.base.filter import (
    EnumFilterOption,
    UUIDFilterOption,
)
from zenml.enums import (
    ResourceRequestReclaimTolerance,
    ResourceRequestStatus,
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

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


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
    quantity: PositiveInt = Field(title="The resource quantity requested.")
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
        ):
            raise ValueError(
                "Resource demands require a resource ID, resource name, or "
                "resource selector."
            )
        return self


class ResourceRequestRequest(UserScopedRequest):
    """Request model for resource requests."""

    component_id: UUID = Field(
        title="The default stack component requesting the resources.",
    )
    candidate_component_ids: list[UUID] = Field(
        default_factory=list,
        title="Candidate stack components that may satisfy the request.",
    )
    step_run_id: UUID = Field(
        title="The step run that is requesting the resources.",
    )
    demands: list[ResourceRequestDemand] = Field(
        default_factory=list,
        title="The resource demands requested.",
    )
    requested_resources: Dict[str, PositiveInt] = Field(
        default_factory=dict,
        title="Compatibility shorthand resources requested by name.",
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = Field(
        default=ResourceRequestReclaimTolerance.UNSAFE,
        title="The capacity reclaim behavior tolerated by this request.",
    )
    lease_expires_at: Optional[datetime] = Field(
        default=None,
        title="The optional initial lease expiration timestamp.",
    )

    @model_validator(mode="after")
    def _normalize_demands(self) -> "ResourceRequestRequest":
        """Normalize compatibility fields into canonical demands.

        Returns:
            The validated resource request.

        Raises:
            ValueError: If no demands were configured.
        """
        if not self.demands and self.requested_resources:
            self.demands = [
                ResourceRequestDemand(resource=name, quantity=quantity)
                for name, quantity in self.requested_resources.items()
            ]

        if not self.requested_resources and self.demands:
            self.requested_resources = {
                demand.resource: demand.quantity
                for demand in self.demands
                if demand.resource is not None
            }

        if not self.demands:
            raise ValueError(
                "Resource requests with no demands are not allowed."
            )

        return self


class ResourceRequestResponseBody(UserScopedResponseBody):
    """Response body for resource requests."""

    component_id: UUID = Field(
        title="The default stack component associated with the request.",
    )
    candidate_component_ids: list[UUID] = Field(
        default_factory=list,
        title="Candidate stack components associated with the request.",
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
    requested_resources: Dict[str, int] = Field(
        default_factory=dict,
        title="Compatibility shorthand resources requested by name.",
    )
    demands: list[ResourceRequestDemand] = Field(
        default_factory=list,
        title="The resource demands requested.",
    )
    status: ResourceRequestStatus = Field(
        title="The status of the resource request."
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = Field(
        title="The capacity reclaim behavior tolerated by this request.",
    )
    lease_expires_at: Optional[datetime] = Field(
        default=None,
        title="The optional lease expiration timestamp.",
    )
    renewed_at: Optional[datetime] = Field(
        default=None,
        title="The optional lease renewal timestamp.",
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
    def component_id(self) -> UUID:
        """Resource request component ID.

        Returns:
            The stack component associated with the resource request.
        """
        return self.get_body().component_id

    @property
    def candidate_component_ids(self) -> list[UUID]:
        """Resource request candidate component IDs.

        Returns:
            The candidate stack components associated with the resource request.
        """
        return self.get_body().candidate_component_ids

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
    def requested_resources(self) -> Dict[str, int]:
        """Requested resources.

        Returns:
            The requested resources keyed by resource name.
        """
        return self.get_body().requested_resources

    @property
    def demands(self) -> list[ResourceRequestDemand]:
        """Requested resource demands.

        Returns:
            The resource demands requested.
        """
        return self.get_body().demands

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

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_id",
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[List[str]] = [
        *UserScopedFilter.API_SINGLE_INPUT_PARAMS,
        "preemptible",
    ]

    reclaim_tolerance: Union[ResourceRequestReclaimTolerance, str, None] = (
        Field(
            default=None,
            description="The reclaim behavior tolerated by the request.",
        )
    )
    component_id: UUIDFilterOption = Field(
        default=None,
        description="The component requesting resources.",
    )
    step_run_id: UUIDFilterOption = Field(
        default=None,
        description="The step run requesting resources.",
    )
    preemption_initiated_by_id: UUIDFilterOption = Field(
        default=None,
        description="The request that initiated preemption.",
    )
    status: EnumFilterOption[ResourceRequestStatus] = Field(
        default=None,
        description="The status of the resource request.",
        union_mode="left_to_right",
    )
    pipeline_run_id: UUIDFilterOption = Field(
        default=None,
        description="The pipeline run requesting resources.",
    )

    def get_custom_filters(
        self,
        table: Type["AnySchema"],
    ) -> List["ColumnElement[bool]"]:
        """Get custom SQL filters for resource request list queries.

        Args:
            table: Schema table used by the generic filter machinery.

        Returns:
            Additional SQL conditions for filters that cannot be represented as
            direct columns on the resource request table.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            ResourceRequestSchema,
            StepRunSchema,
        )

        if self.pipeline_run_id:
            pipeline_run_filters = (
                self.pipeline_run_id
                if isinstance(self.pipeline_run_id, list)
                else [self.pipeline_run_id]
            )
            for pipeline_run_filter in pipeline_run_filters:
                custom_filters.append(
                    and_(
                        ResourceRequestSchema.step_run_id == StepRunSchema.id,
                        self.generate_custom_query_conditions_for_column(
                            value=pipeline_run_filter,
                            table=StepRunSchema,
                            column="pipeline_run_id",
                        ),
                    )
                )

        return custom_filters
