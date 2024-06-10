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
"""Kubernetes pod settings."""

from typing import Any, Dict, List

from pydantic import field_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes import serialization_utils


class KubernetesPodSettings(BaseSettings):
    """Kubernetes Pod settings.

    Attributes:
        node_selectors: Node selectors to apply to the pod.
        affinity: Affinity to apply to the pod.
        tolerations: Tolerations to apply to the pod.
        resources: Resource requests and limits for the pod.
        annotations: Annotations to apply to the pod metadata.
        volumes: Volumes to mount in the pod.
        volume_mounts: Volume mounts to apply to the pod containers.
        host_ipc: Whether to enable host IPC for the pod.
    """

    node_selectors: Dict[str, str] = {}
    affinity: Dict[str, Any] = {}
    tolerations: List[Dict[str, Any]] = []
    resources: Dict[str, Dict[str, str]] = {}
    annotations: Dict[str, str] = {}
    volumes: List[Dict[str, Any]] = []
    volume_mounts: List[Dict[str, Any]] = []
    host_ipc: bool = False

    @field_validator("volumes", mode="before")
    @classmethod
    def _convert_volumes(cls, value: Any) -> Any:
        """Converts Kubernetes volumes to dicts.

        Args:
            value: The volumes list.

        Returns:
            The converted volumes.
        """
        from kubernetes.client.models import V1Volume

        result = []
        for element in value:
            if isinstance(element, V1Volume):
                result.append(
                    serialization_utils.serialize_kubernetes_model(element)
                )
            else:
                result.append(element)

        return result

    @field_validator("volume_mounts", mode="before")
    @classmethod
    def _convert_volume_mounts(cls, value: Any) -> Any:
        """Converts Kubernetes volume mounts to dicts.

        Args:
            value: The volume mounts list.

        Returns:
            The converted volume mounts.
        """
        from kubernetes.client.models import V1VolumeMount

        result = []
        for element in value:
            if isinstance(element, V1VolumeMount):
                result.append(
                    serialization_utils.serialize_kubernetes_model(element)
                )
            else:
                result.append(element)

        return result

    @field_validator("affinity", mode="before")
    @classmethod
    def _convert_affinity(cls, value: Any) -> Any:
        """Converts Kubernetes affinity to a dict.

        Args:
            value: The affinity value.

        Returns:
            The converted value.
        """
        from kubernetes.client.models import V1Affinity

        if isinstance(value, V1Affinity):
            return serialization_utils.serialize_kubernetes_model(value)
        else:
            return value

    @field_validator("tolerations", mode="before")
    @classmethod
    def _convert_tolerations(cls, value: Any) -> Any:
        """Converts Kubernetes tolerations to dicts.

        Args:
            value: The tolerations list.

        Returns:
            The converted tolerations.
        """
        from kubernetes.client.models import V1Toleration

        result = []
        for element in value:
            if isinstance(element, V1Toleration):
                result.append(
                    serialization_utils.serialize_kubernetes_model(element)
                )
            else:
                result.append(element)

        return result

    @field_validator("resources", mode="before")
    @classmethod
    def _convert_resources(cls, value: Any) -> Any:
        """Converts Kubernetes resource requirements to a dict.

        Args:
            value: The resource value.

        Returns:
            The converted value.
        """
        from kubernetes.client.models import V1ResourceRequirements

        if isinstance(value, V1ResourceRequirements):
            return serialization_utils.serialize_kubernetes_model(value)
        else:
            return value
