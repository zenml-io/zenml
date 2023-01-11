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

from typing import List, Optional

from pydantic import BaseModel, Field

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
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

    docstring: Optional[str] = Field(
        title="The docstring of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    spec: PipelineSpec


# -------- #
# RESPONSE #
# -------- #


class PipelineResponseModel(PipelineBaseModel, ProjectScopedResponseModel):
    """Pipeline response model user, project, runs, and status hydrated."""

    runs: Optional[List["PipelineRunResponseModel"]] = Field(
        title="A list of the last x Pipeline Runs."
    )
    status: Optional[List[ExecutionStatus]] = Field(
        title="The status of the last x Pipeline Runs."
    )


# ------- #
# REQUEST #
# ------- #


class PipelineRequestModel(PipelineBaseModel, ProjectScopedRequestModel):
    """Pipeline request model."""


# ------ #
# UPDATE #
# ------ #


@update_model
class PipelineUpdateModel(PipelineRequestModel):
    """Pipeline update model."""
