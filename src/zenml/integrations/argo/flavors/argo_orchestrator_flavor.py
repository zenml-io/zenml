#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Tekton orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.argo import ARGO_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.argo.orchestrators import ArgoOrchestrator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

DEFAULT_ARGO_UI_PORT = 2746


class ArgoOrchestratorSettings(BaseSettings):
    """Settings for the Tekton orchestrator.

    Attributes:
        pod_settings: Pod settings to apply.
    """

    pod_settings: Optional[KubernetesPodSettings] = None
    token: Optional[str] = None  # starting with `Bearer `


class ArgoOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, ArgoOrchestratorSettings
):
    """Configuration for the Argo orchestrator.

    Attributes:
        host: Host of the publicly
        port: Port of the publicly exposed argo service.
        verify_ssl: Whether to verify SSL before deploying the workflow.
        kubernetes_context: Name of a kubernetes context to run
            pipelines in.
        kubernetes_namespace: Name of the kubernetes namespace in which the
            pods that run the pipeline steps should be running.
        skip_ui_daemon_provisioning: If `True`, provisioning the Tekton UI
            daemon will be skipped.
    """

    host: str
    port: int = DEFAULT_ARGO_UI_PORT
    verify_ssl: bool = True
    kubernetes_context: str  # TODO: Potential setting
    kubernetes_namespace: str = "zenml"
    skip_ui_daemon_provisioning: bool = False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class ArgoOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Argo orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return ARGO_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[ArgoOrchestratorConfig]:
        """Returns `ArgoOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return ArgoOrchestratorConfig

    @property
    def implementation_class(self) -> Type["ArgoOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.argo.orchestrators import ArgoOrchestrator

        return ArgoOrchestrator
