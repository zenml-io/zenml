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

from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from kfp.dsl import PipelineTask


def apply_pod_settings(
    pipeline_task: "PipelineTask",
    settings: KubernetesPodSettings,
) -> None:
    """Applies Kubernetes Pod settings to a KFP container.

    Args:
        container_op: The container to which to apply the settings.
        settings: The settings to apply.
    """

    if settings.host_ipc:
        logger.warning(
            "Host IPC is set to `True` but not supported in this orchestrator. "
            "Ignoring..."
        )

    for key, value in settings.node_selectors.items():
        pipeline_task.add_node_selector_constraint(label_name=key, value=value)

    # TODO: add these back in
    # https://github.com/kubeflow/pipelines/issues/9682

    # if settings.affinity:
    #     affinity: V1Affinity = serialization_utils.deserialize_kubernetes_model(
    #         settings.affinity, "V1Affinity"
    #     )
    #     pipeline_task.add_affinity(affinity)

    # for toleration_dict in settings.tolerations:
    #     toleration: V1Toleration = serialization_utils.deserialize_kubernetes_model(
    #         toleration_dict, "V1Toleration"
    #     )
    #     pipeline_task.add_toleration(toleration)

    # if settings.volumes:
    #     for v in settings.volumes:
    #         volume: V1Volume = serialization_utils.deserialize_kubernetes_model(
    #             v, "V1Volume"
    #         )
    #         pipeline_task.add_volume(volume)

    # if settings.volume_mounts:
    #     for v in settings.volume_mounts:
    #         volume_mount: V1VolumeMount = (
    #             serialization_utils.deserialize_kubernetes_model(v, "V1VolumeMount")
    #         )
    #         pipeline_task.container.add_volume_mount(volume_mount)

    # resource_requests = settings.resources.get("requests") or {}
    # for name, value in resource_requests.items():
    #     pipeline_task.add_resource_request(name, value)

    # resource_limits = settings.resources.get("limits") or {}
    # for name, value in resource_limits.items():
    #     pipeline_task.add_resource_limit(name, value)

    # for name, value in settings.annotations.items():
    #     pipeline_task.add_pod_annotation(name, value)
