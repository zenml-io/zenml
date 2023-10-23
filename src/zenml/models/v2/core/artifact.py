#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Models representing artifacts."""

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.config.source import Source, convert_source_validator
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ArtifactType
from zenml.logger import get_logger
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.utils import hydrated_property

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_visualization import (
        ArtifactVisualizationRequest,
        ArtifactVisualizationResponse,
    )
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse
    from zenml.models.v2.core.run_metadata import (
        RunMetadataResponse,
    )
    from zenml.models.v2.core.step_run import StepRunResponse

logger = get_logger(__name__)

# ------------------ Request Model ------------------


class ArtifactRequest(WorkspaceScopedRequest):
    """Request model for artifacts."""

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    uri: str = Field(
        title="URI of the artifact.", max_length=STR_FIELD_MAX_LENGTH
    )
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )
    visualizations: Optional[List["ArtifactVisualizationRequest"]] = Field(
        default=None, title="Visualizations of the artifact."
    )

    _convert_source = convert_source_validator("materializer", "data_type")


# ------------------ Update Model ------------------

# There is no update model for artifacts.

# ------------------ Response Model ------------------


class ArtifactResponseBody(WorkspaceScopedResponseBody):
    """Response body for artifacts."""

    uri: str = Field(
        title="URI of the artifact.", max_length=STR_FIELD_MAX_LENGTH
    )
    type: ArtifactType = Field(title="Type of the artifact.")


class ArtifactResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for artifacts."""

    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    producer_step_run_id: Optional[UUID] = Field(
        title="ID of the step run that produced this artifact.",
        default=None,
    )
    visualizations: Optional[List["ArtifactVisualizationResponse"]] = Field(
        default=None, title="Visualizations of the artifact."
    )
    run_metadata: Dict[str, "RunMetadataResponse"] = Field(
        default={}, title="Metadata of the artifact."
    )
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )

    _convert_source = convert_source_validator("materializer", "data_type")


class ArtifactResponse(WorkspaceScopedResponse):
    """Response model for artifacts."""

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata pair
    body: "ArtifactResponseBody"
    metadata: Optional["ArtifactResponseMetadata"]

    def get_hydrated_version(self) -> "ArtifactResponse":
        """Get the hydrated version of this artifact."""
        from zenml.client import Client

        return Client().zen_store.get_artifact(self.id)

    # Body and metadata properties
    @property
    def uri(self):
        """The `uri` property."""
        return self.body.uri

    @property
    def type(self):
        """The `type` property."""
        return self.body.type

    @hydrated_property
    def artifact_store_id(self):
        """The `artifact_store_id` property."""
        return self.metadata.artifact_store_id

    @hydrated_property
    def producer_step_run_id(self):
        """The `producer_step_run_id` property."""
        return self.metadata.producer_step_run_id

    @hydrated_property
    def visualizations(self):
        """The `visualizations` property."""
        return self.metadata.visualizations

    @hydrated_property
    def run_metadata(self):
        """The `metadata` property."""
        return self.metadata.run_metadata

    @hydrated_property
    def materializer(self):
        """The `materializer` property."""
        return self.metadata.materializer

    @hydrated_property
    def data_type(self):
        """The `data_type` property."""
        return self.metadata.data_type

    # Helper methods
    @property
    def step(self) -> "StepRunResponse":
        """Get the step that produced this artifact.

        Returns:
            The step that produced this artifact.
        """
        from zenml.utils.artifact_utils import get_producer_step_of_artifact

        return get_producer_step_of_artifact(self)

    @property
    def run(self) -> "PipelineRunResponse":
        """Get the pipeline run that produced this artifact.

        Returns:
            The pipeline run that produced this artifact.
        """
        return self.step.run

    def load(self) -> Any:
        """Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        from zenml.utils.artifact_utils import load_artifact

        return load_artifact(self)

    def read(self) -> Any:
        """(Deprecated) Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        logger.warning(
            "`artifact.read()` is deprecated and will be removed in a future "
            "release. Please use `artifact.load()` instead."
        )
        return self.load()

    def visualize(self, title: Optional[str] = None) -> None:
        """Visualize the artifact in notebook environments.

        Args:
            title: Optional title to show before the visualizations.
        """
        from zenml.utils.visualization_utils import visualize_artifact

        visualize_artifact(self, title=title)


# ------------------ Filter Model ------------------


class ArtifactFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Artifacts."""

    # `only_unused` refers to a property of the artifacts relationship
    #  rather than a field in the db, hence it needs to be handled
    #  explicitly
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "only_unused",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the artifact",
    )
    uri: Optional[str] = Field(
        default=None,
        description="Uri of the artifact",
    )
    materializer: Optional[str] = Field(
        default=None,
        description="Materializer used to produce the artifact",
    )
    type: Optional[str] = Field(
        default=None,
        description="Type of the artifact",
    )
    data_type: Optional[str] = Field(
        default=None,
        description="Datatype of the artifact",
    )
    artifact_store_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Artifact store for this artifact"
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace for this artifact"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User that produced this artifact"
    )
    only_unused: Optional[bool] = Field(
        default=False, description="Filter only for unused artifacts"
    )
