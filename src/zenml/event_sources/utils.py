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

from zenml.enums import PluginType
from zenml.plugins.plugin_flavor_registry import PluginFlavorRegistry


def fail_if_invalid_event_filter_configuration(
    flavor: str,
    plugin_type: PluginType,
    configuration_dict: Dict[str, Any],
) -> bool:
    """Validate the configuration of an event filter.

    Args:
        flavor: Name of the flavor
        plugin_type: The type of plugin
        configuration_dict: The event filter configuration to validate.

    Returns:
        True if the configuration is valid

    Raises:
        ValueError: If the configuration is invalid.
    """
    event_configuration_class = (
        PluginFlavorRegistry()
        .get_flavor_class(flavor, plugin_type)
        .EVENT_FILTER_CONFIG_CLASS
    )
    try:
        event_configuration_class(**configuration_dict)
    except ValueError:
        raise ValueError("Invalid Configuration.")
    except KeyError:
        raise ValueError(f"Event Filter Flavor {flavor} does not exist.")
    else:
        return True
