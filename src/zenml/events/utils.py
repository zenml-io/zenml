from typing import Dict, Any

from zenml.enums import EventConfigurationType
from zenml.events.event_flavor_registry import \
    event_configuration_registry


def validate_event_config(
    event_type: str,
    event_configuration_type: EventConfigurationType,
    configuration_dict: Dict[str, Any],
) -> bool:
    """Validate the configuration of an event filter.

    Args:
        configuration_dict: The event filter configuration to validate.
        event_type: The type of the event that is being configured.
        event_configuration_type: Type of event configuration [SOURCE, FILTER]

    Returns:
        True if the configuration is valid

    Raises:
        ValueError: If the configuration is invalid.
    """
    if event_configuration_type == EventConfigurationType.SOURCE:
        event_configuration_class = event_configuration_registry.get_event_source_flavor(event_type)
    elif event_configuration_type == EventConfigurationType.FILTER:
        event_configuration_class = event_configuration_registry.get_event_filter_flavor(event_type)
    else:
        raise ValueError(f"Invalid event configuration type {event_configuration_type}.")
    try:
        event_configuration_class(**configuration_dict)
    except ValueError:
        return False
    else:
        return True