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
"""Models representing artifact versions."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.source import Source, convert_source_validator
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ArtifactType, LogicalOperators
from zenml.logger import get_logger
from zenml.models.tag_models import TagResponseModel
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.core.artifact import ArtifactResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
    from sqlmodel import SQLModel

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


class ArtifactVersionRequest(WorkspaceScopedRequest):
    """Request model for artifact versions."""

    artifact_id: UUID = Field(
        title="ID of the artifact to which this version belongs.",
    )
    version: Union[str, int] = Field(
        title="Version of the artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    uri: str = Field(
        title="URI of the artifact.", max_length=TEXT_FIELD_MAX_LENGTH
    )
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )
    tags: Optional[List[str]] = Field(
        title="Tags of the artifact.",
        description="Should be a list of plain strings, e.g., ['tag1', 'tag2']",
        default=None,
    )
    visualizations: Optional[List["ArtifactVisualizationRequest"]] = Field(
        default=None, title="Visualizations of the artifact."
    )

    _convert_source = convert_source_validator("materializer", "data_type")


# ------------------ Update Model ------------------


class ArtifactVersionUpdate(BaseModel):
    """Artifact version update model."""

    name: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None


# ------------------ Response Model ------------------


class ArtifactVersionResponseBody(WorkspaceScopedResponseBody):
    """Response body for artifact versions."""

    artifact: ArtifactResponse = Field(
        title="Artifact to which this version belongs."
    )
    version: Union[str, int] = Field(
        title="Version of the artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    uri: str = Field(
        title="URI of the artifact.", max_length=TEXT_FIELD_MAX_LENGTH
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )
    tags: List[TagResponseModel] = Field(
        title="Tags associated with the model",
    )

    _convert_source = convert_source_validator("materializer", "data_type")


class ArtifactVersionResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for artifact versions."""

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


class ArtifactVersionResponse(
    WorkspaceScopedResponse[
        ArtifactVersionResponseBody, ArtifactVersionResponseMetadata
    ]
):
    """Response model for artifact versions."""

    def get_hydrated_version(self) -> "ArtifactVersionResponse":
        """Get the hydrated version of this artifact version.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_artifact_version(self.id)

    # Body and metadata properties
    @property
    def artifact(self) -> "ArtifactResponse":
        """The `artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().artifact

    @property
    def version(self) -> Union[str, int]:
        """The `version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().version

    @property
    def uri(self) -> str:
        """The `uri` property.

        Returns:
            the value of the property.
        """
        return self.get_body().uri

    @property
    def type(self) -> ArtifactType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def tags(self) -> List[TagResponseModel]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tags

    @property
    def artifact_store_id(self) -> Optional[UUID]:
        """The `artifact_store_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().artifact_store_id

    @property
    def producer_step_run_id(self) -> Optional[UUID]:
        """The `producer_step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().producer_step_run_id

    @property
    def visualizations(
        self,
    ) -> Optional[List["ArtifactVisualizationResponse"]]:
        """The `visualizations` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().visualizations

    @property
    def run_metadata(self) -> Dict[str, "RunMetadataResponse"]:
        """The `metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    @property
    def materializer(self) -> Source:
        """The `materializer` property.

        Returns:
            the value of the property.
        """
        return self.get_body().materializer

    @property
    def data_type(self) -> Source:
        """The `data_type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().data_type

    # Helper methods
    @property
    def name(self) -> str:
        """The `name` property.

        Returns:
            the value of the property.
        """
        return self.artifact.name

    @property
    def step(self) -> "StepRunResponse":
        """Get the step that produced this artifact.

        Returns:
            The step that produced this artifact.
        """
        from zenml.artifacts.utils import get_producer_step_of_artifact

        return get_producer_step_of_artifact(self)

    @property
    def run(self) -> "PipelineRunResponse":
        """Get the pipeline run that produced this artifact.

        Returns:
            The pipeline run that produced this artifact.
        """
        from zenml.client import Client

        return Client().get_pipeline_run(self.step.pipeline_run_id)

    def load(self) -> Any:
        """Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        from zenml.artifacts.utils import load_artifact_from_response

        return load_artifact_from_response(self)

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


class ArtifactVersionFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of artifact versions."""

    # `name` and `only_unused` refer to properties related to other entities
    #  rather than a field in the db, hence they needs to be handled
    #  explicitly
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "name",
        "only_unused",
    ]
    artifact_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="ID of the artifact to which this version belongs.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the artifact to which this version belongs.",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the artifact",
    )
    version_number: Optional[Union[int, str]] = Field(
        default=None,
        description="Version of the artifact if it is an integer",
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

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the filter for the query.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_, or_

        from zenml.zen_stores.schemas import (
            ArtifactSchema,
            ArtifactVersionSchema,
        )

        base_filter = super().generate_filter(table)

        operator = (
            or_ if self.logical_operator == LogicalOperators.OR else and_
        )

        if self.name:
            artifact_name_filter = and_(  # type: ignore[type-var]
                ArtifactSchema.name == self.name,
                ArtifactVersionSchema.artifact_id == ArtifactSchema.id,
            )
            base_filter = operator(base_filter, artifact_name_filter)

        return base_filter
