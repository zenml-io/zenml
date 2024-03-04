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
"""Models representing event source flavors.."""

from typing import Any, Dict

from zenml.models.v2.base.base_plugin_flavor import (
    BasePluginFlavorResponse,
    BasePluginResponseBody,
    BasePluginResponseMetadata,
    BasePluginResponseResources,
)


class EventSourceFlavorResponseBody(BasePluginResponseBody):
    """Response body for event flavors."""


class EventSourceFlavorResponseMetadata(BasePluginResponseMetadata):
    """Response metadata for event flavors."""

    source_config_schema: Dict[str, Any]
    filter_config_schema: Dict[str, Any]


class EventSourceFlavorResponseResources(BasePluginResponseResources):
    """Response resources for event source flavors."""


class EventSourceFlavorResponse(
    BasePluginFlavorResponse[
        EventSourceFlavorResponseBody,
        EventSourceFlavorResponseMetadata,
        EventSourceFlavorResponseResources,
    ]
):
    """Response model for Event Source Flavors."""

    # Body and metadata properties
    @property
    def source_config_schema(self) -> Dict[str, Any]:
        """The `source_config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source_config_schema

    @property
    def filter_config_schema(self) -> Dict[str, Any]:
        """The `filter_config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().filter_config_schema
