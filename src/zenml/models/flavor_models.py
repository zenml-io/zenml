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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.base_models import (
    UserScopedRequestModel,
    UserScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH

if TYPE_CHECKING:
    from zenml.models import ProjectResponseModel

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
    config_schema: Dict[str, Any] = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
    )
    source: str = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    logo_url: str = Field(
        default="https://3376789856-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/collections%2FUoWo1UaWzv9Bv1r8FK4K%2Ficon%2F9FC5shDCotdkDPemxZZ3%2F02%20-%20Logo.png?alt=media&token=ab93a501-d807-4c49-94cd-5aa56f2434ec"
    )


# -------- #
# RESPONSE #
# -------- #


class FlavorResponseModel(FlavorBaseModel, UserScopedResponseModel):
    """Response model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "integration",
    ]

    project: Optional["ProjectResponseModel"] = Field(
        title="The project of this resource."
    )


# ------- #
# REQUEST #
# ------- #


class FlavorRequestModel(FlavorBaseModel, UserScopedRequestModel):
    """Request model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "integration",
    ]

    project: Optional[UUID] = Field(
        title="The project to which this resource belongs."
    )
