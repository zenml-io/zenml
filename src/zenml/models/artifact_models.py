#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from pydantic import BaseModel, Field

from zenml.config.source import Source, convert_source_validator
from zenml.enums import ArtifactType
from zenml.logger import get_logger
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.visualization_models import VisualizationModel

if TYPE_CHECKING:
    from zenml.models.pipeline_run_models import PipelineRunResponseModel
    from zenml.models.run_metadata_models import RunMetadataResponseModel
    from zenml.models.step_run_models import StepRunResponseModel


logger = get_logger(__name__)

# ---- #
# BASE #
# ---- #


class ArtifactBaseModel(BaseModel):
    """Base model for artifacts."""

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    uri: str = Field(
        title="URI of the artifact.", max_length=STR_FIELD_MAX_LENGTH
    )
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )
    visualizations: Optional[List[VisualizationModel]] = Field(
        default=None, title="Visualizations of the artifact."
    )

    _convert_source = convert_source_validator("materializer", "data_type")


# -------- #
# RESPONSE #
# -------- #


class ArtifactResponseModel(ArtifactBaseModel, WorkspaceScopedResponseModel):
    """Response model for artifacts."""

    producer_step_run_id: Optional[UUID] = Field(
        title="ID of the step run that produced this artifact.",
        default=None,
    )
    metadata: Dict[str, "RunMetadataResponseModel"] = Field(
        default={}, title="Metadata of the artifact."
    )

    @property
    def step(self) -> "StepRunResponseModel":
        """Get the step that produced this artifact.

        Returns:
            The step that produced this artifact.
        """
        from zenml.utils.artifact_utils import get_producer_step_of_artifact

        return get_producer_step_of_artifact(self)

    @property
    def run(self) -> "PipelineRunResponseModel":
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


# ------ #
# FILTER #
# ------ #


class ArtifactFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Artifacts."""

    # `only_unused` refers to a property of the artifacts relationship
    #  rather than a field in the db, hence it needs to be handled
    #  explicitly
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
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


# ------- #
# REQUEST #
# ------- #


class ArtifactRequestModel(ArtifactBaseModel, WorkspaceScopedRequestModel):
    """Request model for artifacts."""
