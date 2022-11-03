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
"""KFP utilities."""


from typing import TYPE_CHECKING

from zenml.integrations.kubernetes import serialization_utils
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

if TYPE_CHECKING:
    from kfp.dsl import ContainerOp


def apply_pod_settings(
    container_op: "ContainerOp",
    settings: KubernetesPodSettings,
) -> None:
    """Applies Kubernetes Pod settings to a KFP container.

    Args:
        container_op: The container to which to apply the settings.
        settings: The settings to apply.
    """
    from kubernetes.client.models import V1Affinity, V1Toleration

    for key, value in settings.node_selectors.items():
        container_op.add_node_selector_constraint(label_name=key, value=value)

    if settings.affinity:
        affinity: V1Affinity = serialization_utils.deserialize_kubernetes_model(
            settings.affinity, "V1Affinity"
        )
        container_op.add_affinity(affinity)

    for toleration_dict in settings.tolerations:
        toleration: V1Toleration = (
            serialization_utils.deserialize_kubernetes_model(
                toleration_dict, "V1Toleration"
            )
        )
        container_op.add_toleration(toleration)
