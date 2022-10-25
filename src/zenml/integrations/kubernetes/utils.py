import re
from datetime import date, datetime
from typing import Any, Dict, List, Type, cast

import kubernetes.client.models


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
    """Serializes any object.

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
    type_mapping = cast(Dict[str, str], model_class.openapi_types)
    reverse_attribute_mapping = cast(Dict[str, str], model_class.attribute_map)
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


from typing import Union

from kubernetes.client.models import V1Affinity, V1Toleration
from pydantic import validator

from zenml.config.base_settings import BaseSettings


class KubernetesPodSettings(BaseSettings):
    """Kubernetes Pod settings.

    Attributes:
        node_selectors: Node selectors to apply to the pod.
        affinity: Affinity to apply to the pod.
        tolerations: Tolerations to apply to the pod.
    """

    node_selectors: Dict[str, str] = {}
    affinity: Dict[str, Any] = {}
    tolerations: List[Dict[str, Any]] = []

    @validator("affinity", pre=True)
    def _convert_affinity(
        cls, value: Union[Dict[str, Any], V1Affinity]
    ) -> Dict[str, Any]:
        """Converts Kubernetes affinity to a dict.

        Args:
            value: The affinity value.

        Returns:
            The converted value.
        """
        if isinstance(value, V1Affinity):
            return serialize_kubernetes_model(value)
        else:
            return value

    @validator("tolerations", pre=True)
    def _convert_tolerations(
        cls, value: List[Union[Dict[str, Any], V1Toleration]]
    ) -> List[Dict[str, Any]]:
        """Converts Kubernetes tolerations to dicts.

        Args:
            value: The tolerations list.

        Returns:
            The converted tolerations.
        """
        result = []
        for element in value:
            if isinstance(element, V1Toleration):
                result.append(serialize_kubernetes_model(element))
            else:
                result.append(element)

        return result


from kfp.dsl import ContainerOp


def apply_pod_settings(
    container_op: "ContainerOp", settings: KubernetesPodSettings
) -> None:
    """Applies Kubernetes Pod settings to a container.

    Args:
        container_op: The container to which to apply the settings.
        settings: The settings to apply.
    """
    for key, value in settings.node_selectors.items():
        container_op.add_node_selector_constraint(label_name=key, value=value)

    if settings.affinity:
        affinity: V1Affinity = deserialize_kubernetes_model(
            settings.affinity, "V1Affinity"
        )
        container_op.add_affinity(affinity)

    for toleration_dict in settings.tolerations:
        toleration: V1Toleration = deserialize_kubernetes_model(
            toleration_dict, "V1Toleration"
        )
        container_op.add_toleration(toleration)
