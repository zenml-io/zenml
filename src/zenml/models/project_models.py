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
"""Models representing projects."""


from pydantic import BaseModel, Field

from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH


# ---- #
# BASE #
# ---- #
class ProjectBaseModel(BaseModel):
    """Base model for projects."""

    name: str = Field(
        title="The unique name of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class ProjectResponseModel(ProjectBaseModel, BaseResponseModel):
    """Response model for projects."""


# ------- #
# REQUEST #
# ------- #


class ProjectRequestModel(ProjectBaseModel, BaseRequestModel):
    """Request model for projects."""


# ------ #
# UPDATE #
# ------ #


@update_model
class ProjectUpdateModel(ProjectRequestModel):
    """Update model for projects."""
