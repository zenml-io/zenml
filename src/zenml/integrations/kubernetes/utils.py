import re
from typing import Any, Dict, List, Type, cast

import kubernetes.client.models


def serialize_kubernetes_model(model: object) -> Dict[str, Any]:
    if not is_model_class(model.__class__.__name__):
        raise TypeError(f"Unable to serialize non-kubernetes model {model}.")
    assert hasattr(model, "to_dict")
    return cast(Dict[str, Any], model.to_dict())


def deserialize_kubernetes_model(data: Dict[str, Any], class_name: str) -> Any:
    model_class = get_model_class(class_name=class_name)
    assert hasattr(model_class, "openapi_types")
    attribute_mapping = cast(Dict[str, str], model_class.openapi_types)

    deserialized_attributes: Dict[str, Any] = {}

    for key, value in data.items():
        if key not in attribute_mapping:
            raise KeyError(
                f"Got value for attribute {key} which is not one of the "
                f"available attributes {set(attribute_mapping)}."
            )

        attribute_class = attribute_mapping[key]

        if not value:
            deserialized_attributes[key] = value
        elif attribute_class.startswith("list["):
            inner_class = re.match(r"list\[(.*)\]", attribute_class).group(1)
            deserialized_attributes[key] = _deserialize_list(
                value, class_name=inner_class
            )
        elif attribute_class.startswith("dict("):
            inner_class = re.match(
                r"dict\(([^,]*), (.*)\)", attribute_class
            ).group(2)
            deserialized_attributes[key] = _deserialize_dict(
                value, class_name=inner_class
            )
        elif is_model_class(attribute_class):
            deserialized_attributes[key] = deserialize_kubernetes_model(
                value, attribute_class
            )
        else:
            deserialized_attributes[key] = value

    return model_class(**deserialized_attributes)


def is_model_class(class_name: str) -> bool:
    return hasattr(kubernetes.client.models, class_name)


def get_model_class(class_name: str) -> Type[Any]:
    class_ = getattr(kubernetes.client.models, class_name, None)

    if not class_:
        raise TypeError(
            f"Unable to find kubernetes model class with name {class_name}."
        )

    return class_


def _deserialize_list(data: Any, class_name: str) -> List[Any]:
    assert isinstance(data, List)
    if is_model_class(class_name):
        return [
            deserialize_kubernetes_model(element, class_name)
            for element in data
        ]
    else:
        return data


def _deserialize_dict(data: Any, class_name: str) -> Dict[str, Any]:
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
    node_selectors: Dict[str, str] = {}
    affinity: Dict[str, Any] = {}
    tolerations: List[Dict[str, Any]] = []

    @validator("affinity", pre=True)
    def _convert_affinity(
        cls, value: Union[Dict[str, Any], V1Affinity]
    ) -> Dict[str, Any]:
        if isinstance(value, V1Affinity):
            return serialize_kubernetes_model(value)
        else:
            return value

    @validator("tolerations", pre=True)
    def _convert_tolerations(
        cls, value: List[Union[Dict[str, Any], V1Toleration]]
    ) -> Dict[str, Any]:
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
