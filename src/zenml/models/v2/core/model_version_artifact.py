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
"""Models representing the link between model versions and artifacts."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from uuid import UUID

from pydantic import Field, validator

from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
)

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse


# ------------------ Request Model ------------------


class ModelVersionArtifactRequest(WorkspaceScopedRequest):
    """Request model for links between model versions and artifacts."""

    model: UUID
    model_version: UUID
    artifact_version: UUID
    is_model_artifact: bool = False
    is_deployment_artifact: bool = False

    @validator("is_deployment_artifact")
    def _validate_is_endpoint_artifact(
        cls, is_deployment_artifact: bool, values: Dict[str, Any]
    ) -> bool:
        is_model_artifact = values.get("is_model_artifact", False)
        if is_model_artifact and is_deployment_artifact:
            raise ValueError(
                "Artifact cannot be a model artifact and deployment artifact "
                "at the same time."
            )
        return is_deployment_artifact


# ------------------ Update Model ------------------

# There is no update model for links between model version and artifacts.

# ------------------ Response Model ------------------


class ModelVersionArtifactResponseBody(BaseResponseBody):
    """Response body for links between model versions and artifacts."""

    model: UUID
    model_version: UUID
    artifact_version: "ArtifactVersionResponse"
    is_model_artifact: bool = False
    is_deployment_artifact: bool = False


class ModelVersionArtifactResponse(
    BaseResponse[ModelVersionArtifactResponseBody, BaseResponseMetadata]
):
    """Response model for links between model versions and artifacts."""

    # Body and metadata properties
    @property
    def model(self) -> UUID:
        """The `model` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model

    @property
    def model_version(self) -> UUID:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version

    @property
    def artifact_version(self) -> "ArtifactVersionResponse":
        """The `artifact_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().artifact_version

    @property
    def is_model_artifact(self) -> bool:
        """The `is_model_artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_model_artifact

    @property
    def is_deployment_artifact(self) -> bool:
        """The `is_deployment_artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_deployment_artifact


# ------------------ Filter Model ------------------


class ModelVersionArtifactFilter(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    # Artifact name and type are not DB fields and need to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "artifact_name",
        "only_data_artifacts",
        "only_model_artifacts",
        "only_deployment_artifacts",
    ]

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    model_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model ID"
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model version ID"
    )
    artifact_version_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by artifact ID"
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Name of the artifact",
    )
    only_data_artifacts: Optional[bool] = False
    only_model_artifacts: Optional[bool] = False
    only_deployment_artifacts: Optional[bool] = False

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "only_data_artifacts",
        "only_model_artifacts",
        "only_deployment_artifacts",
        "model_id",
        "model_version_id",
        "user_id",
        "workspace_id",
        "updated",
        "id",
    ]
