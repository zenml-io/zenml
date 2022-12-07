#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Kubernetes serialization utils."""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Type, cast


def serialize_kubernetes_model(model: Any) -> Dict[str, Any]:
    """Serializes a Kubernetes model.

    Args:
        model: The model to serialize.

    Raises:
        TypeError: If the model is not a Kubernetes model.

    Returns:
        The serialized model.
    """
    if not is_model_class(model.__class__.__name__):
        raise TypeError(f"Unable to serialize non-kubernetes model {model}.")

    assert hasattr(model, "attribute_map")
    attribute_mapping = cast(Dict[str, str], model.attribute_map)

    model_attributes = {
        serialized_attribute_name: getattr(model, attribute_name)
        for attribute_name, serialized_attribute_name in attribute_mapping.items()
    }
    return _serialize_dict(model_attributes)


def _serialize_dict(dict_: Dict[str, Any]) -> Dict[str, Any]:
    """Serializes a dictionary.

    Args:
        dict_: Dict to serialize.

    Returns:
        The serialized dict.
    """
    return {key: _serialize(value) for key, value in dict_.items()}


def _serialize(value: Any) -> Any:
    """Serializes any valid object.

    Args:
        value: The object to serialize.

    Raises:
        TypeError: If the object is not serializable.

    Returns:
        The serialized object.
    """
    primitive_types = (float, bool, bytes, str, int)

    if value is None:
        return None
    elif isinstance(value, primitive_types):
        return value
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, List):
        return [_serialize(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(_serialize(item) for item in value)
    elif isinstance(value, Dict):
        return _serialize_dict(value)
    elif is_model_class(value.__class__.__name__):
        return serialize_kubernetes_model(value)
    else:
        raise TypeError(f"Failed to serialize unknown object {value}")


def deserialize_kubernetes_model(data: Dict[str, Any], class_name: str) -> Any:
    """Deserializes a Kubernetes model.

    Args:
        data: The model data.
        class_name: Name of the Kubernetes model class.

    Raises:
        KeyError: If the data contains values for an invalid attribute.

    Returns:
        The deserialized model.
    """
    model_class = get_model_class(class_name=class_name)
    assert hasattr(model_class, "openapi_types")
    assert hasattr(model_class, "attribute_map")
    # Mapping of the attribute name of the model class to the attribute type
    type_mapping = cast(Dict[str, str], model_class.openapi_types)
    reverse_attribute_mapping = cast(Dict[str, str], model_class.attribute_map)
    # Mapping of the serialized key to the attribute name of the model class
    attribute_mapping = {
        value: key for key, value in reverse_attribute_mapping.items()
    }

    deserialized_attributes: Dict[str, Any] = {}

    for key, value in data.items():
        if key not in attribute_mapping:
            raise KeyError(
                f"Got value for attribute {key} which is not one of the "
                f"available attributes {set(attribute_mapping)}."
            )

        attribute_name = attribute_mapping[key]
        attribute_class = type_mapping[attribute_name]

        if not value:
            deserialized_attributes[attribute_name] = value
        elif attribute_class.startswith("list["):
            match = re.fullmatch(r"list\[(.*)\]", attribute_class)
            assert match
            inner_class = match.group(1)
            deserialized_attributes[attribute_name] = _deserialize_list(
                value, class_name=inner_class
            )
        elif attribute_class.startswith("dict("):
            match = re.fullmatch(r"dict\(([^,]*), (.*)\)", attribute_class)
            assert match
            inner_class = match.group(1)
            deserialized_attributes[attribute_name] = _deserialize_dict(
                value, class_name=inner_class
            )
        elif is_model_class(attribute_class):
            deserialized_attributes[
                attribute_name
            ] = deserialize_kubernetes_model(value, attribute_class)
        else:
            deserialized_attributes[attribute_name] = value

    return model_class(**deserialized_attributes)


def is_model_class(class_name: str) -> bool:
    """Checks whether the given class name is a Kubernetes model class.

    Args:
        class_name: Name of the class to check.

    Returns:
        If the given class name is a Kubernetes model class.
    """
    import kubernetes.client.models

    return hasattr(kubernetes.client.models, class_name)


def get_model_class(class_name: str) -> Type[Any]:
    """Gets a Kubernetes model class.

    Args:
        class_name: Name of the class to get.

    Raises:
        TypeError: If no Kubernetes model class exists for this name.

    Returns:
        The model class.
    """
    import kubernetes.client.models

    class_ = getattr(kubernetes.client.models, class_name, None)

    if not class_:
        raise TypeError(
            f"Unable to find kubernetes model class with name {class_name}."
        )

    assert isinstance(class_, type)
    return class_


def _deserialize_list(data: Any, class_name: str) -> List[Any]:
    """Deserializes a list of potential Kubernetes models.

    Args:
        data: The data to deserialize.
        class_name: Name of the class of the elements of the list.

    Returns:
        The deserialized list.
    """
    assert isinstance(data, List)
    if is_model_class(class_name):
        return [
            deserialize_kubernetes_model(element, class_name)
            for element in data
        ]
    else:
        return data


def _deserialize_dict(data: Any, class_name: str) -> Dict[str, Any]:
    """Deserializes a dict of potential Kubernetes models.

    Args:
        data: The data to deserialize.
        class_name: Name of the class of the elements of the dict.

    Returns:
        The deserialized dict.
    """
    assert isinstance(data, Dict)
    if is_model_class(class_name):
        return {
            key: deserialize_kubernetes_model(value, class_name)
            for key, value in data.items()
        }
    else:
        return data
