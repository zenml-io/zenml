#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Plugin flavor model definitions."""
from typing import Generic, TypeVar

from pydantic import Extra, Field

from zenml.enums import PluginSubType, PluginType
from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseMetadata,
    BaseZenModel,
)


class BasePluginResponseBody(BaseZenModel):
    """Response body for plugins."""


class BasePluginResponseMetadata(BaseResponseMetadata):
    """Response metadata for plugins."""


AnyPluginBody = TypeVar("AnyPluginBody", bound=BasePluginResponseBody)
AnyPluginMetadata = TypeVar(
    "AnyPluginMetadata", bound=BasePluginResponseMetadata
)


class BasePluginFlavorResponse(
    BaseResponse[AnyPluginBody, AnyPluginMetadata],
    Generic[AnyPluginBody, AnyPluginMetadata],
):
    """Base response for all Plugin Flavors."""

    flavor_name: str = Field(title="Name of the flavor.")
    plugin_type: PluginType = Field(title="Type of the flavor.")
    plugin_subtype: PluginSubType = Field(title="Subtype of the flavor.")

    class Config:
        """Configuration for base plugin flavor response."""

        extra = Extra.allow
