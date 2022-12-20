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

from typing import TYPE_CHECKING, ClassVar, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import FlavorFieldDataType, StackComponentType
from zenml.models.base_models import (
    UserScopedRequestModel,
    UserScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH

if TYPE_CHECKING:
    from zenml.models import ProjectResponseModel


class FlavorConfigurationField(BaseModel):
    """Serializable representation that defines one specific configuration field of a Flavor Configuration Model."""

    field_name: str
    datatype: FlavorFieldDataType
    is_required: bool
    description: str

    @staticmethod
    def convert_to_flavor_datatype(datatype: type) -> FlavorFieldDataType:
        """Convert a python datatype into an enum value for serialization.

        Args:
            datatype: Field datatype

        Returns:
            String representation of that datatype.
        """
        if datatype == str:
            return FlavorFieldDataType.STRING
        elif datatype == int:
            return FlavorFieldDataType.INT
        elif datatype == float:
            return FlavorFieldDataType.FLOAT
        elif datatype == bool:
            return FlavorFieldDataType.BOOL
        elif datatype == list:
            return FlavorFieldDataType.LIST
        elif datatype == dict:
            return FlavorFieldDataType.DICT
        else:
            return FlavorFieldDataType.ANY


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
    logo_url: str = Field(default="https://tinyurl.com/m4xab3yj")

    configuration: List[FlavorConfigurationField] = Field(default=[])


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
