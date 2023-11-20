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

from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import Field, validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    ModelVersionScopedFilter,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    WorkspaceScopedRequest,
)

# ------------------ Request Model ------------------


class ModelVersionArtifactRequest(WorkspaceScopedRequest):
    """Request model for model version and artifact links."""

    name: Optional[str] = Field(
        description="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_name: Optional[str] = Field(
        description="The name of the pipeline creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    step_name: Optional[str] = Field(
        description="The name of the step creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact: UUID
    model: UUID
    model_version: UUID
    is_model_artifact: bool = False
    is_endpoint_artifact: bool = False

    overwrite: bool = False

    @validator("is_endpoint_artifact")
    def _validate_is_endpoint_artifact(
        cls, is_endpoint_artifact: bool, values: Dict[str, Any]
    ) -> bool:
        is_model_artifact = values.get("is_model_artifact", False)

        if is_model_artifact and is_endpoint_artifact:
            raise ValueError(
                "Artifact cannot be a model artifact and endpoint artifact "
                "at the same time."
            )
        return is_endpoint_artifact


# ------------------ Update Model ------------------

# There is no update models for model version and artifact links.

# ------------------ Response Model ------------------


class ModelVersionArtifactResponseBody(UserScopedResponseBody):
    """Response body for model version and artifact links."""

    name: Optional[str] = Field(
        description="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_name: Optional[str] = Field(
        description="The name of the pipeline creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    step_name: Optional[str] = Field(
        description="The name of the step creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact: UUID
    model: UUID
    model_version: UUID
    is_model_artifact: bool = False
    is_endpoint_artifact: bool = False

    link_version: int

    @validator("is_endpoint_artifact")
    def _validate_is_endpoint_artifact(
        cls, is_endpoint_artifact: bool, values: Dict[str, Any]
    ) -> bool:
        is_model_artifact = values.get("is_model_artifact", False)
        if is_model_artifact and is_endpoint_artifact:
            raise ValueError(
                "Artifact cannot be a model artifact and endpoint artifact "
                "at the same time."
            )
        return is_endpoint_artifact


class ModelVersionArtifactResponse(
    UserScopedResponse[
        ModelVersionArtifactResponseBody, UserScopedResponseMetadata
    ]
):
    """Response model for model version and artifact links."""

    # Body and metadata properties
    @property
    def name(self) -> Optional[str]:
        """The `name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().name

    @property
    def pipeline_name(self) -> Optional[str]:
        """The `pipeline_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline_name

    @property
    def step_name(self) -> Optional[str]:
        """The `step_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().step_name

    @property
    def artifact(self) -> UUID:
        """The `artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().artifact

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
    def is_model_artifact(self) -> bool:
        """The `is_model_artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_model_artifact

    @property
    def is_endpoint_artifact(self) -> bool:
        """The `is_endpoint_artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_endpoint_artifact

    @property
    def link_version(self) -> int:
        """The `link_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().link_version


# ------------------ Filter Model ------------------


class ModelVersionArtifactFilter(ModelVersionScopedFilter):
    """Model version pipeline run links filter model."""

    name: Optional[str] = Field(
        description="The name of the artifact inside model version.",
    )
    pipeline_name: Optional[str] = Field(
        description="The name of the pipeline creating this artifact.",
    )
    step_name: Optional[str] = Field(
        description="The name of the step creating this artifact.",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    only_data_artifacts: Optional[bool] = False
    only_model_artifacts: Optional[bool] = False
    only_endpoint_artifacts: Optional[bool] = False

    CLI_EXCLUDE_FIELDS = [
        *ModelVersionScopedFilter.CLI_EXCLUDE_FIELDS,
        "only_data_artifacts",
        "only_model_artifacts",
        "only_endpoint_artifacts",
        "user_id",
        "workspace_id",
        "scope_workspace",
        "updated",
        "id",
    ]
