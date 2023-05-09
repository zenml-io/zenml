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
"""Models representing roles that can be assigned to users or teams."""

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
    artifact_store_id: Union[str, UUID] = None


# -------- #
# RESPONSE #
# -------- #


class LogsResponseModel(LogsBaseModel, BaseResponseModel):
    """Response model for logs."""

    step_run_id: Optional[Union[str, UUID]] = None
    pipeline_run_id: Optional[Union[str, UUID]] = None


# ------- #
# REQUEST #
# ------- #


class LogsRequestModel(LogsBaseModel, BaseRequestModel):
    """Request model for logs."""
