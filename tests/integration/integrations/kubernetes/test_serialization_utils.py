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

from typing import Any, List

import pytest
from kubernetes import client as k8s_client

from zenml.integrations.kubernetes.serialization_utils import (
    deserialize_kubernetes_model,
    get_model_class,
    serialize_kubernetes_model,
)


def _create_test_models() -> List[Any]:
    """Creates test kubernetes models."""
    match_expressions = [
        k8s_client.V1NodeSelectorRequirement(
            key="k",
            operator="In",
            values=["v1", "v2"],
        ),
        k8s_client.V1NodeSelectorRequirement(
            key="k2",
            operator="Contains",
            values=["v3", "v2"],
        ),
    ]

    affinity = k8s_client.V1Affinity(
        node_affinity=k8s_client.V1NodeAffinity(
            required_during_scheduling_ignored_during_execution=k8s_client.V1NodeSelector(
                node_selector_terms=[
                    k8s_client.V1NodeSelectorTerm(
                        match_expressions=match_expressions
                    )
                ]
            )
        )
    )

    toleration = k8s_client.V1Toleration(
        key="key", operator="Equal", value="value", effect="NoExecute"
    )

    volume = k8s_client.V1Volume(
        name="cache-volume",
        empty_dir=k8s_client.V1EmptyDirVolumeSource(
            medium="Memory", size_limit="1Gi"
        ),
    )

    volume_mount = k8s_client.V1VolumeMount(
        mount_path="/dev/shm",  # nosec
        name="cache-volume",
    )

    return [affinity, toleration, volume, volume_mount]


@pytest.mark.parametrize("model", _create_test_models())
def test_model_serialization_and_deserialization(model: Any) -> None:
    """Tests that kubernetes models get serialized and deserialized correctly."""
    model_dict = serialize_kubernetes_model(model)
    deserialized_model = deserialize_kubernetes_model(
        model_dict, class_name=model.__class__.__name__
    )
    assert model == deserialized_model


def test_get_model_class() -> None:
    """Tests the `get_model_class` function."""
    assert get_model_class("V1Affinity") is k8s_client.V1Affinity

    with pytest.raises(TypeError):
        get_model_class("not_a_kubernetes_model_class")


def test_serializing_invalid_model() -> None:
    """Tests that trying to serialize a non-kubernetes model raises an error."""
    with pytest.raises(TypeError):
        serialize_kubernetes_model(5)


def test_deserializing_invalid_model() -> None:
    """Tests that trying to deserialize to a non-kubernetes model raises an error."""
    with pytest.raises(TypeError):
        deserialize_kubernetes_model({}, "not_a_kubernetes_model_class")
