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
"""Utils for event sources and event filters."""
from typing import Any, Dict

from zenml.enums import PluginSubType, PluginType
from zenml.event_sources.base_event_source import (
    BaseEventSource,
)
from zenml.plugins.plugin_flavor_registry import plugin_flavor_registry


def validate_event_filter_configuration(
    flavor: str,
    plugin_type: PluginType,
    plugin_subtype: PluginSubType,
    configuration_dict: Dict[str, Any],
) -> None:
    """Validate the configuration of an event filter.

    Args:
        flavor: Name of the flavor
        plugin_type: The type of plugin
        plugin_subtype: The subtype of plugin
        configuration_dict: The event filter configuration to validate.

    Raises:
        RuntimeError: If an event source plugin does not exist for the plugin
            flavor, type, and subtype.
    """
    event_source_plugin = plugin_flavor_registry.get_plugin(
        flavor=flavor, _type=plugin_type, subtype=plugin_subtype
    )

    if not isinstance(event_source_plugin, BaseEventSource):
        raise RuntimeError(
            f"Event source plugin does not exist for flavor {flavor}, "
            f"type {plugin_type}, and subtype {plugin_subtype}."
        )

    event_source_plugin.validate_event_filter_configuration(configuration_dict)
