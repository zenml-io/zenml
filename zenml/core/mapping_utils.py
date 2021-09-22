from typing import Dict, Text, Type

from zenml.core.base_component import BaseComponent


def get_component_from_key(
    key: Text, mapping: Dict[Text, Type[BaseComponent]]
) -> BaseComponent:
    """Given a key and a mapping, return an initialized component.

    Args:
        key: Unique key.
        mapping: Dict of type Text --> Class.

    Returns:

    """
    class_ = mapping[key]
    return class_(uuid=key)
