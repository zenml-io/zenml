#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Models representing Pipeline Endpoints."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import PipelineEndpointStatus
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models.v2.core.component import ComponentResponse
    from zenml.models.v2.core.pipeline_deployment import (
        PipelineDeploymentResponse,
    )


class PipelineEndpointOperationalState(BaseModel):
    """Operational state of a pipeline endpoint."""

    status: PipelineEndpointStatus = Field(
        default=PipelineEndpointStatus.UNKNOWN
    )
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ------------------ Request Model ------------------


class PipelineEndpointRequest(ProjectScopedRequest):
    """Request model for pipeline endpoints."""

    name: str = Field(
        title="The name of the pipeline endpoint.",
        description="A unique name for the pipeline endpoint within the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_deployment_id: UUID = Field(
        title="The pipeline deployment ID.",
        description="The ID of the pipeline deployment being served by this endpoint.",
    )
    deployer_id: UUID = Field(
        title="The deployer ID.",
        description="The ID of the deployer component managing this endpoint.",
    )


# ------------------ Update Model ------------------


class PipelineEndpointUpdate(BaseUpdate):
    """Update model for pipeline endpoints."""

    name: Optional[str] = Field(
        default=None,
        title="The new name of the pipeline endpoint.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_deployment_id: Optional[UUID] = Field(
        default=None,
        title="New pipeline deployment ID.",
    )
    url: Optional[str] = Field(
        default=None,
        title="The new URL of the pipeline endpoint.",
    )
    status: Optional[str] = Field(
        default=None,
        title="The new status of the pipeline endpoint.",
    )
    endpoint_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The new metadata of the pipeline endpoint.",
    )

    @classmethod
    def from_operational_state(
        cls, operational_state: PipelineEndpointOperationalState
    ) -> "PipelineEndpointUpdate":
        """Create an update from an operational state.

        Args:
            operational_state: The operational state to create an update from.

        Returns:
            The update.
        """
        return cls(
            status=operational_state.status,
            url=operational_state.url,
            endpoint_metadata=operational_state.metadata,
        )


# ------------------ Response Model ------------------


class PipelineEndpointResponseBody(ProjectScopedResponseBody):
    """Response body for pipeline endpoints."""

    url: Optional[str] = Field(
        default=None,
        title="The URL of the pipeline endpoint.",
        description="The HTTP URL where the pipeline endpoint can be accessed.",
    )
    status: Optional[str] = Field(
        default=None,
        title="The status of the pipeline endpoint.",
        description="Current operational status of the pipeline endpoint.",
    )


class PipelineEndpointResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for pipeline endpoints."""

    pipeline_deployment_id: Optional[UUID] = Field(
        default=None,
        title="The pipeline deployment ID.",
        description="The ID of the pipeline deployment being served by this endpoint.",
    )
    deployer_id: Optional[UUID] = Field(
        default=None,
        title="The deployer ID.",
        description="The ID of the deployer component managing this endpoint.",
    )
    endpoint_metadata: Dict[str, Any] = Field(
        title="The metadata of the pipeline endpoint.",
    )


class PipelineEndpointResponseResources(ProjectScopedResponseResources):
    """Response resources for pipeline endpoints."""

    pipeline_deployment: Optional["PipelineDeploymentResponse"] = Field(
        default=None,
        title="The pipeline deployment.",
        description="The pipeline deployment being served by this endpoint.",
    )
    deployer: Optional["ComponentResponse"] = Field(
        default=None,
        title="The deployer.",
        description="The deployer component managing this endpoint.",
    )


class PipelineEndpointResponse(
    ProjectScopedResponse[
        PipelineEndpointResponseBody,
        PipelineEndpointResponseMetadata,
        PipelineEndpointResponseResources,
    ]
):
    """Response model for pipeline endpoints."""

    name: str = Field(
        title="The name of the pipeline endpoint.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineEndpointResponse":
        """Get the hydrated version of this pipeline endpoint.

        Returns:
            an instance of the same entity with the metadata and resources fields
            attached.
        """
        from zenml.client import Client

        client = Client()
        return client.get_pipeline_endpoint(self.id)

    # Helper properties
    @property
    def url(self) -> Optional[str]:
        """The URL of the pipeline endpoint.

        Returns:
            The URL of the pipeline endpoint.
        """
        return self.get_body().url

    @property
    def status(self) -> Optional[str]:
        """The status of the pipeline endpoint.

        Returns:
            The status of the pipeline endpoint.
        """
        return self.get_body().status

    @property
    def pipeline_deployment_id(self) -> Optional[UUID]:
        """The pipeline deployment ID.

        Returns:
            The pipeline deployment ID.
        """
        return self.get_metadata().pipeline_deployment_id

    @property
    def deployer_id(self) -> Optional[UUID]:
        """The deployer ID.

        Returns:
            The deployer ID.
        """
        return self.get_metadata().deployer_id

    @property
    def endpoint_metadata(self) -> Dict[str, Any]:
        """The metadata of the pipeline endpoint.

        Returns:
            The metadata of the pipeline endpoint.
        """
        return self.get_metadata().endpoint_metadata

    @property
    def pipeline_deployment(self) -> Optional["PipelineDeploymentResponse"]:
        """The pipeline deployment.

        Returns:
            The pipeline deployment.
        """
        return self.get_resources().pipeline_deployment

    @property
    def deployer(self) -> Optional["ComponentResponse"]:
        """The deployer.

        Returns:
            The deployer.
        """
        return self.get_resources().deployer


# ------------------ Filter Model ------------------


class PipelineEndpointFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of pipeline endpoints."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline endpoint.",
    )
    url: Optional[str] = Field(
        default=None,
        description="URL of the pipeline endpoint.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Status of the pipeline endpoint.",
    )
    pipeline_deployment_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline deployment ID associated with the endpoint.",
        union_mode="left_to_right",
    )
    deployer_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Deployer ID managing the endpoint.",
        union_mode="left_to_right",
    )
