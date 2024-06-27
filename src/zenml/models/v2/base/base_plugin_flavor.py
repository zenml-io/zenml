#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

from pydantic import ConfigDict, Field

from zenml.enums import PluginSubType, PluginType
from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
)


class BasePluginResponseBody(BaseResponseBody):
    """Response body for plugins."""


class BasePluginResponseMetadata(BaseResponseMetadata):
    """Response metadata for plugins."""


class BasePluginResponseResources(BaseResponseResources):
    """Response resources for plugins."""


AnyPluginBody = TypeVar("AnyPluginBody", bound=BasePluginResponseBody)
AnyPluginMetadata = TypeVar(
    "AnyPluginMetadata", bound=BasePluginResponseMetadata
)
AnyPluginResources = TypeVar(
    "AnyPluginResources", bound=BasePluginResponseResources
)


class BasePluginFlavorResponse(
    BaseResponse[AnyPluginBody, AnyPluginMetadata, AnyPluginResources],
    Generic[AnyPluginBody, AnyPluginMetadata, AnyPluginResources],
):
    """Base response for all Plugin Flavors."""

    name: str = Field(title="Name of the flavor.")
    type: PluginType = Field(title="Type of the plugin.")
    subtype: PluginSubType = Field(title="Subtype of the plugin.")
    model_config = ConfigDict(extra="ignore")

    def get_hydrated_version(
        self,
    ) -> "BasePluginFlavorResponse[AnyPluginBody, AnyPluginMetadata, AnyPluginResources]":
        """Abstract method to fetch the hydrated version of the model.

        Returns:
            Hydrated version of the PluginFlavorResponse
        """
        # TODO: shouldn't this call the Zen store ? The client should not have
        #  to know about the plugin flavor registry
        from zenml.zen_server.utils import plugin_flavor_registry

        plugin_flavor = plugin_flavor_registry().get_flavor_class(
            name=self.name, _type=self.type, subtype=self.subtype
        )
        return plugin_flavor.get_flavor_response_model(hydrate=True)
