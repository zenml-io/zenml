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
"""Assistant flavor model definitions."""

from zenml.models.v2.base.base_plugin_flavor import (
    BasePluginFlavorResponse,
    BasePluginResponseBody,
    BasePluginResponseMetadata,
    BasePluginResponseResources,
)


class AssistantFlavorResponseBody(BasePluginResponseBody):
    """Response body for assistant flavors."""


class AssistantFlavorResponseMetadata(BasePluginResponseMetadata):
    """Response metadata for assistant flavors."""


class AssistantFlavorResponseResources(BasePluginResponseResources):
    """Response resources for assistant flavors."""


class AssistantFlavorResponse(
    BasePluginFlavorResponse[
        AssistantFlavorResponseBody,
        AssistantFlavorResponseMetadata,
        AssistantFlavorResponseResources,
    ]
):
    """Response model for Assistant Flavors."""
