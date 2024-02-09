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

from zenml.models.v2.plugin.plugin_flavor import (
    BasePluginFlavorResponse,
    BasePluginResponseBody,
    BasePluginResponseMetadata
)


class EventFlavorResponseBody(BasePluginResponseBody):
    """Response body for event flavors."""


class EventFlavorResponseMetadata(BasePluginResponseMetadata):
    """Response metadata for event flavors."""

    source_config_schema: Dict[str, Any]
    filter_config_schema: Dict[str, Any]


class EventFlavorResponse(
    BasePluginFlavorResponse[EventFlavorResponseBody, EventFlavorResponseMetadata]
):
    """Response model for Event Flavors."""
