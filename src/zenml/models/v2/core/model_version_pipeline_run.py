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

from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import Field

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
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse

# ------------------ Request Model ------------------


class ModelVersionPipelineRunRequest(WorkspaceScopedRequest):
    """Request model for links between model versions and pipeline runs."""

    model: UUID
    model_version: UUID
    pipeline_run: UUID


# ------------------ Update Model ------------------

# There is no update model for links between model version and pipeline runs.

# ------------------ Response Model ------------------


class ModelVersionPipelineRunResponseBody(BaseResponseBody):
    """Response body for links between model versions and pipeline runs."""

    model: UUID
    model_version: UUID
    pipeline_run: "PipelineRunResponse"


class ModelVersionPipelineRunResponse(
    BaseResponse[ModelVersionPipelineRunResponseBody, BaseResponseMetadata]
):
    """Response model for links between model versions and pipeline runs."""

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
    def pipeline_run(self) -> "PipelineRunResponse":
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline_run


# ------------------ Filter Model ------------------


class ModelVersionPipelineRunFilter(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    # Pipeline run name is not a DB field and needs to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_name",
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
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by pipeline run ID"
    )
    pipeline_run_name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline run",
    )

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "model_id",
        "model_version_id",
        "user_id",
        "workspace_id",
        "updated",
        "id",
    ]
