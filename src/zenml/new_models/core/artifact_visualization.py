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
from typing import Optional, Union
from uuid import UUID

from zenml.enums import VisualizationType
from zenml.new_models.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseMetadata,
)

# ------------------ Request Model ------------------


class ArtifactVisualizationRequest(BaseRequest):
    """Request model for artifact visualization."""

    type: VisualizationType
    uri: str
    artifact_id: UUID


# ------------------ Update Model ------------------

# There is no update model for artifact visualizations.

# ------------------ Response Model ------------------


class ArtifactVisualizationResponseMetadata(BaseResponseMetadata):
    """Response metadata model for artifact visualizations."""
    artifact_id: UUID

class ArtifactVisualizationResponse(BaseResponse):
    """Response model for artifact visualizations."""

    # Entity fields
    type: VisualizationType
    uri: str
    value: Union[str, bytes]

    # Metadata related field, method and properties
    metadata: Optional["ArtifactVisualizationResponseMetadata"]

    def get_hydrated_version(self) -> "ArtifactVisualizationResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_artifact_visualization(self.id)
