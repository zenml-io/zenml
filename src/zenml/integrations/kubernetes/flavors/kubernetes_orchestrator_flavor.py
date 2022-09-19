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
"""Kubernetes orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.kubernetes import KUBERNETES_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.orchestrators import (
        KubernetesOrchestrator,
    )


class KubernetesOrchestratorConfig(BaseOrchestratorConfig):
    """Configuration for the Kubernetes orchestrator.

    Attributes:
        custom_docker_base_image_name: Name of a Docker image that should be
            used as the base for the image that will be run on Kubernetes pods.
            If no custom image is given, a basic image of the active ZenML
            version will be used.
            **Note**: This image needs to have ZenML installed,
            otherwise the pipeline execution will fail. For that reason, you
            might want to extend the ZenML Docker images found here:
            https://hub.docker.com/r/zenmldocker/zenml/
        kubernetes_context: Optional name of a Kubernetes context to run
            pipelines in. If not set, the current active context will be used.
            You can find the active context by running `kubectl config
            current-context`.
        kubernetes_namespace: Name of the Kubernetes namespace to be used.
            If not provided, `default` namespace will be used.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on Kubernetes.
        skip_config_loading: If `True`, don't load the Kubernetes context and
            clients. This is only useful for unit testing.
    """

    custom_docker_base_image_name: Optional[str] = None
    kubernetes_context: Optional[str] = None
    kubernetes_namespace: str = "zenml"
    synchronous: bool = False
    skip_config_loading: bool = False

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("custom_docker_base_image_name", "docker_parent_image")
    )


class KubernetesOrchestratorFlavor(BaseOrchestratorFlavor):
    """Kubernetes orchestrator flavor."""

    @property
    def name(self) -> str:
        return KUBERNETES_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[KubernetesOrchestratorConfig]:
        return KubernetesOrchestratorConfig

    @property
    def implementation_class(self) -> Type["KubernetesOrchestrator"]:
        from zenml.integrations.kubernetes.orchestrators import (
            KubernetesOrchestrator,
        )

        return KubernetesOrchestrator
