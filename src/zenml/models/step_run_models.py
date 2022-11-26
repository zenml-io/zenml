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

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import ExecutionStatus
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH

# ---- #
# BASE #
# ---- #


class StepRunBaseModel(BaseModel):
    """Base model for step runs."""

    name: str = Field(
        title="The name of the pipeline run step.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    pipeline_run_id: UUID
    parent_step_ids: List[UUID]
    input_artifacts: Dict[str, UUID]
    status: ExecutionStatus

    entrypoint_name: str
    parameters: Dict[str, str]
    step_configuration: Dict[str, Any]
    docstring: Optional[str]
    num_outputs: Optional[int]

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: Optional[int]
    mlmd_parent_step_ids: List[int]


# -------- #
# RESPONSE #
# -------- #


class StepRunResponseModel(StepRunBaseModel, BaseResponseModel):
    """Response model for step runs."""


# ------- #
# REQUEST #
# ------- #


class StepRunRequestModel(StepRunBaseModel, BaseRequestModel):
    """Request model for step runs."""


# ------ #
# UPDATE #
# ------ #
@update_model
class StepRunUpdateModel(StepRunRequestModel):
    """Update model for step runs."""
