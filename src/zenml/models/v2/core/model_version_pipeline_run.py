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
"""Models representing the link between model versions and pipeline runs."""

from typing import Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    ModelVersionScopedFilter,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    WorkspaceScopedRequest,
)

# ------------------ Request Model ------------------


class ModelVersionPipelineRunRequest(WorkspaceScopedRequest):
    """Request model for model version and pipeline run links."""

    name: Optional[str] = Field(
        description="The name of the pipeline run inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_run: UUID
    model: UUID
    model_version: UUID


# ------------------ Update Model ------------------

# There is no update models for model version and artifact links.

# ------------------ Response Model ------------------


class ModelVersionPipelineRunResponseBody(UserScopedResponseBody):
    """Response body for model version and pipeline run links."""

    name: Optional[str] = Field(
        description="The name of the pipeline run inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_run: UUID
    model: UUID
    model_version: UUID


class ModelVersionPipelineRunResponse(
    UserScopedResponse[
        ModelVersionPipelineRunResponseBody, UserScopedResponseMetadata
    ]
):
    """Response model for model version and pipeline run links."""

    # Body and metadata properties
    @property
    def name(self) -> Optional[str]:
        """The `name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().name

    @property
    def pipeline_run(self) -> UUID:
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline_run

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


# ------------------ Filter Model ------------------


class ModelVersionPipelineRunFilter(ModelVersionScopedFilter):
    """Model version pipeline run links filter model."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
