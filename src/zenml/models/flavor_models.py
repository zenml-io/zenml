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
"""Models representing stack component flavors."""

from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH

# ---- #
# BASE #
# ---- #


class FlavorBaseModel(BaseModel):
    """Base model for stack component flavors."""

    name: str = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(title="The type of the Flavor.")
    config_schema: str = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source: str = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class FlavorResponseModel(FlavorBaseModel, ProjectScopedResponseModel):
    """Response model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "integration",
    ]


# ------- #
# REQUEST #
# ------- #


class FlavorRequestModel(FlavorBaseModel, ProjectScopedRequestModel):
    """Request model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "integration",
    ]
