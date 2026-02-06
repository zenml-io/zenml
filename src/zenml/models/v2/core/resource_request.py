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
    Union,
)
from uuid import UUID

from pydantic import Field, PositiveInt, model_validator

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
    step_run_id: Optional[UUID] = Field(
        title="The id of the step run that is requesting the resources.",
        default=None,
    )
    requested_resources: Dict[str, PositiveInt] = Field(
        title="The resources requested."
    )

    @model_validator(mode="after")
    def _validate_requested_resources(self) -> "ResourceRequestRequest":
        if not self.requested_resources:
            raise ValueError(
                "Resource requests with no requested resources are not allowed."
            )

        return self


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
    status_reason: Optional[str] = Field(
        title="The reason for the status of the resource request.",
        default=None,
    )


class ResourceRequestResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource requests."""

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
    pipeline_run: Optional["PipelineRunResponse"] = Field(
        title="The pipeline run that is requesting the resources.",
        default=None,
    )
    preempted_by: Optional["ResourceRequestResponse"] = Field(
        title="The request that preempted this request.", default=None
    )
    running_in_pool: Optional["ResourcePoolResponse"] = Field(
        title="The pool that the resource request is running in.", default=None
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
        return self.get_body().status_reason

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

    @property
    def pipeline_run(self) -> Optional["PipelineRunResponse"]:
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pipeline_run

    @property
    def preempted_by(self) -> Optional["ResourceRequestResponse"]:
        """The `preempted_by` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().preempted_by

    @property
    def running_in_pool(self) -> Optional["ResourcePoolResponse"]:
        """The `running_in_pool` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().running_in_pool


# ------------------ Filter Model ------------------


class ResourceRequestFilter(UserScopedFilter):
    """Resource request filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_id",
    ]

    component_id: Union[UUID, str, None] = Field(
        default=None,
        description="The id of the component that is requesting the resources.",
    )
    step_run_id: Union[UUID, str, None] = Field(
        default=None,
        description="The id of the step run that is requesting the resources.",
    )
    preempted_by_id: Union[UUID, str, None] = Field(
        default=None,
        description="The id of the request that preempted this request.",
    )
    status: Union[ResourceRequestStatus, str, None] = Field(
        default=None,
        description="The status of the resource request.",
    )
    pipeline_run_id: Union[UUID, str, None] = Field(
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
            pipeline_run_filter = and_(
                ResourceRequestSchema.step_run_id == StepRunSchema.id,
                StepRunSchema.pipeline_run_id == self.pipeline_run_id,
            )
            custom_filters.append(pipeline_run_filter)

        return custom_filters
