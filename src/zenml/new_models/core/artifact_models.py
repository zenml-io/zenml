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

from pydantic import Field
from uuid import UUID
from typing import Optional, List, Dict, TYPE_CHECKING
from zenml.enums import ArtifactType
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.new_models.base import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    WorkspaceScopedResponseMetadataModel,
)
from zenml.config.source import Source, convert_source_validator

if TYPE_CHECKING:
    from zenml.new_models.core.visualization_models import \
        VisualizationResponseModel
    from zenml.new_models.core.run_metadata_models import \
        RunMetadataResponseModel


# ------------------ Request Model ------------------


class ArtifactRequestModel(WorkspaceScopedRequestModel):
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
    visualizations: Optional[List["VisualizationResponseModel"]] = Field(
        default=None, title="Visualizations of the artifact."
    )

    _convert_source = convert_source_validator("materializer", "data_type")


# ------------------ Update Model ------------------

# There is no update models for artifacts.

# ------------------ Response Model ------------------

class ArtifactResponseMetadataModel(WorkspaceScopedResponseMetadataModel):
    """Response metadata model for artifacts."""
    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    producer_step_run_id: Optional[UUID] = Field(
        title="ID of the step run that produced this artifact.",
        default=None,
    )
    visualizations: Optional[List["VisualizationResponseModel"]] = Field(
        default=None, title="Visualizations of the artifact."
    )
    metadata: Dict[str, "RunMetadataResponseModel"] = Field(
        default={}, title="Metadata of the artifact."
    )
    materializer: Source = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: Source = Field(
        title="Data type of the artifact.",
    )

    _convert_source = convert_source_validator("materializer", "data_type")


class ArtifactResponseModel(WorkspaceScopedResponseModel):
    """Response model for artifacts."""

    # Metadata Association
    metadata: Optional[ArtifactResponseMetadataModel]

    # Fields
    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    uri: str = Field(
        title="URI of the artifact.", max_length=STR_FIELD_MAX_LENGTH
    )
    type: ArtifactType = Field(title="Type of the artifact.")

    @property
    def artifact_store_id(self):
        return self.metadata.artifact_store_id

    def get_metadata(self) -> "WorkspaceScopedResponseMetadataModel":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client
        artifact = Client().get_artifact(self.id)
        return ArtifactResponseMetadataModel(
            artifact_store_id=artifact.artifact_store_id,
            producer_step_run_id=artifact.producer_step_run_id,

        )

