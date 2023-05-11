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
"""Models representing logs files."""

from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.constants import STR_FIELD_MAX_LENGTH

# ---- #
# BASE #
# ---- #


class LogsBaseModel(BaseModel):
    """Base model for logs."""

    uri: str = Field(
        title="The uri of the logs file",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact_store_id: Union[str, UUID] = Field(
        title="The artifact store ID to associate the logs with.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class LogsResponseModel(LogsBaseModel, BaseResponseModel):
    """Response model for logs."""

    step_run_id: Optional[Union[str, UUID]] = Field(
        title="Step ID to associate the logs with.",
        default=None,
        description="When this is set, pipeline_run_id should be set to None.",
    )
    pipeline_run_id: Optional[Union[str, UUID]] = Field(
        title="Pipeline run ID to associate the logs with.",
        default=None,
        description="When this is set, step_run_id should be set to None.",
    )


# ------- #
# REQUEST #
# ------- #


class LogsRequestModel(LogsBaseModel, BaseRequestModel):
    """Request model for logs."""
