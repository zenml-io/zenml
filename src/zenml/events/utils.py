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

from zenml.enums import EventConfigurationType
from zenml.events.event_flavor_registry import event_configuration_registry


def validate_event_config(
    event_flavor: str,
    event_configuration_type: EventConfigurationType,
    configuration_dict: Dict[str, Any],
) -> bool:
    """Validate the configuration of an event filter.

    Args:
        configuration_dict: The event filter configuration to validate.
        event_flavor: The flavor of the event that is being configured.
        event_configuration_type: Type of event configuration [SOURCE, FILTER]

    Returns:
        True if the configuration is valid

    Raises:
        ValueError: If the configuration is invalid.
    """
    if event_configuration_type == EventConfigurationType.SOURCE:
        event_configuration_class = (
            event_configuration_registry.get_event_flavor(event_flavor)
        )
    elif event_configuration_type == EventConfigurationType.FILTER:
        event_configuration_class = (
            event_configuration_registry.get_event_filter_flavor(event_flavor)
        )
    else:
        raise ValueError(
            f"Invalid event configuration type {event_configuration_type}."
        )
    try:
        event_configuration_class(**configuration_dict)
    except ValueError:
        return False
    else:
        return True
