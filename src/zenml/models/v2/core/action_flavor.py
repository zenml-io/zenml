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
"""Action flavor model definitions."""

from typing import Any, Dict

from zenml.models.v2.base.base_plugin_flavor import (
    BasePluginFlavorResponse,
    BasePluginResponseBody,
    BasePluginResponseMetadata,
    BasePluginResponseResources,
)


class ActionFlavorResponseBody(BasePluginResponseBody):
    """Response body for action flavors."""


class ActionFlavorResponseMetadata(BasePluginResponseMetadata):
    """Response metadata for action flavors."""

    config_schema: Dict[str, Any]


class ActionFlavorResponseResources(BasePluginResponseResources):
    """Response resources for action flavors."""


class ActionFlavorResponse(
    BasePluginFlavorResponse[
        ActionFlavorResponseBody,
        ActionFlavorResponseMetadata,
        ActionFlavorResponseResources,
    ]
):
    """Response model for Action Flavors."""

    # Body and metadata properties
    @property
    def config_schema(self) -> Dict[str, Any]:
        """The `source_config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_schema
