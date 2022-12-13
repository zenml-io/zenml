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
"""Models representing steps of pipeline runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH

if TYPE_CHECKING:
    from zenml.models import ArtifactResponseModel

# ---- #
# BASE #
# ---- #


class StepRunBaseModel(BaseModel):
    """Base model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    step: Step
    pipeline_run_id: UUID
    original_step_run_id: Optional[UUID] = None
    status: ExecutionStatus
    parent_step_ids: List[UUID] = []
    cache_key: Optional[str] = Field(
        title="The cache key of the step run.",
        default=None,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# -------- #
# RESPONSE #
# -------- #


class StepRunResponseModel(StepRunBaseModel, ProjectScopedResponseModel):
    """Response model for step runs."""

    input_artifacts: Dict[str, "ArtifactResponseModel"] = {}
    output_artifacts: Dict[str, "ArtifactResponseModel"] = {}


# ------- #
# REQUEST #
# ------- #


class StepRunRequestModel(StepRunBaseModel, ProjectScopedRequestModel):
    """Request model for step runs."""

    input_artifacts: Dict[str, UUID] = {}
    output_artifacts: Dict[str, UUID] = {}


# ------ #
# UPDATE #
# ------ #


class StepRunUpdateModel(BaseModel):
    """Update model for step runs."""

    output_artifacts: Dict[str, UUID] = {}
    status: Optional[ExecutionStatus] = None
    end_time: Optional[datetime] = None
