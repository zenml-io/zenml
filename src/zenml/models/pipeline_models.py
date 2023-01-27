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
"""Models representing pipelines."""

from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.pipeline_run_models import PipelineRunResponseModel

# ---- #
# BASE #
# ---- #


class PipelineBaseModel(BaseModel):
    """Base model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version: str = Field(
        title="The version of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version_hash: str = Field(
        title="The version hash of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: Optional[str] = Field(
        title="The docstring of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    spec: PipelineSpec


# -------- #
# RESPONSE #
# -------- #


class PipelineResponseModel(PipelineBaseModel, WorkspaceScopedResponseModel):
    """Pipeline response model user, workspace, runs, and status hydrated."""

    runs: Optional[List["PipelineRunResponseModel"]] = Field(
        title="A list of the last x Pipeline Runs."
    )
    status: Optional[List[ExecutionStatus]] = Field(
        title="The status of the last x Pipeline Runs."
    )


# ------ #
# FILTER #
# ------ #


class PipelineFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Workspaces."""

    name: str = Field(
        default=None,
        description="Name of the Pipeline",
    )
    version: str = Field(
        default=None,
        description="Version of the Pipeline",
    )
    version_hash: str = Field(
        default=None,
        description="Version hash of the Pipeline",
    )
    docstring: str = Field(
        default=None,
        description="Docstring of the Pipeline",
    )
    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace of the Pipeline"
    )
    user_id: Union[UUID, str] = Field(None, description="User of the Pipeline")


# ------- #
# REQUEST #
# ------- #


class PipelineRequestModel(PipelineBaseModel, WorkspaceScopedRequestModel):
    """Pipeline request model."""


# ------ #
# UPDATE #
# ------ #


@update_model
class PipelineUpdateModel(PipelineRequestModel):
    """Pipeline update model."""
