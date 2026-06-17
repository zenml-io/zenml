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
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import Field, PositiveInt, model_validator

from zenml.enums import ResourceRequestStatus
from zenml.models.v2.base.filter import (
    EnumFilterOption,
    UUIDFilterOption,
)
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

    from zenml.models import (
        ComponentResponse,
        PipelineRunResponse,
        StepRunResponse,
    )
    from zenml.models.v2.core.resource_pool import ResourcePoolResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class ResourceRequestRequest(UserScopedRequest):
    """Request model for resource requests."""

    component_id: UUID = Field(
        title="The id of the component that is requesting the resources.",
    )
    step_run_id: UUID = Field(
        title="The id of the step run that is requesting the resources.",
    )
    requested_resources: Dict[str, PositiveInt] = Field(
        title="The resources requested."
    )
    preemptible: bool = Field(
        default=True,
        title="Whether this request can be preempted.",
    )

    @model_validator(mode="after")
    def _validate_requested_resources(self) -> "ResourceRequestRequest":
        if not self.requested_resources:
            raise ValueError(
                "Resource requests with no requested resources are not allowed."
            )

        return self


# ------------------ Response Model ------------------


class ResourceRequestResponseBody(UserScopedResponseBody):
    """Response body for resource requests."""

    requested_resources: Dict[str, int] = Field(
        title="The resources requested."
    )
    status: ResourceRequestStatus = Field(
        title="The status of the resource request."
    )
    status_reason: Optional[str] = Field(
        title="The reason for the status of the resource request.",
        default=None,
    )
    preemptible: bool = Field(
        title="Whether this request can be preempted.",
    )


class ResourceRequestResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource requests."""


class ResourceRequestResponseResources(UserScopedResponseResources):
    """Response resources for resource requests."""

    component: Optional["ComponentResponse"] = Field(
        title="The component that is requesting the resources.",
        default=None,
    )
    step_run: Optional["StepRunResponse"] = Field(
        title="The step run that is requesting the resources.", default=None
    )
    pipeline_run: Optional["PipelineRunResponse"] = Field(
        title="The pipeline run that is requesting the resources.",
        default=None,
    )
    pool: Optional["ResourcePoolResponse"] = Field(
        title="The pool that the resource request is/was running in.",
        default=None,
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
        return self.get_body().requested_resources

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
        return self.get_body().status_reason

    @property
    def preemptible(self) -> bool:
        """The `preemptible` property.

        Returns:
            the value of the property.
        """
        return self.get_body().preemptible

    @property
    def component(self) -> Optional["ComponentResponse"]:
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

    @property
    def pipeline_run(self) -> Optional["PipelineRunResponse"]:
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pipeline_run

    @property
    def pool(self) -> Optional["ResourcePoolResponse"]:
        """The `pool` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pool


# ------------------ Filter Model ------------------


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

    preemptible: Optional[bool] = Field(
        default=None,
        description="Whether the resource request is preemptible.",
    )
    component_id: UUIDFilterOption = Field(
        default=None,
        description="The id of the component that is requesting the resources.",
    )
    step_run_id: UUIDFilterOption = Field(
        default=None,
        description="The id of the step run that is requesting the resources.",
    )
    preemption_initiated_by_id: UUIDFilterOption = Field(
        default=None,
        description="The id of the request that initiated the preemption of this request.",
    )
    status: EnumFilterOption[ResourceRequestStatus] = Field(
        default=None,
        description="The status of the resource request.",
        union_mode="left_to_right",
    )
    pipeline_run_id: UUIDFilterOption = Field(
        default=None,
        description="The id of the pipeline run that is requesting the resources.",
    )

    def get_custom_filters(
        self,
        table: Type["AnySchema"],
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
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
