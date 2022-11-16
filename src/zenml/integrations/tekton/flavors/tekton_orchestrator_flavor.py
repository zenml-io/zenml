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
"""Tekton orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.tekton import TEKTON_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.tekton.orchestrators import TektonOrchestrator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

DEFAULT_TEKTON_UI_PORT = 8080


class TektonOrchestratorSettings(BaseSettings):
    """Settings for the Tekton orchestrator.

    Attributes:
        pod_settings: Pod settings to apply.
    """

    pod_settings: Optional[KubernetesPodSettings] = None


class TektonOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, TektonOrchestratorSettings
):
    """Configuration for the Tekton orchestrator.

    Attributes:
        kubernetes_context: Name of a kubernetes context to run
            pipelines in.
        kubernetes_namespace: Name of the kubernetes namespace in which the
            pods that run the pipeline steps should be running.
        tekton_ui_port: A local port to which the Tekton UI will be forwarded.
        skip_ui_daemon_provisioning: If `True`, provisioning the Tekton UI
            daemon will be skipped.
    """

    kubernetes_context: str  # TODO: Potential setting
    kubernetes_namespace: str = "zenml"
    tekton_ui_port: int = DEFAULT_TEKTON_UI_PORT
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


class TektonOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Tekton orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return TEKTON_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[TektonOrchestratorConfig]:
        """Returns `TektonOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return TektonOrchestratorConfig

    @property
    def implementation_class(self) -> Type["TektonOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.tekton.orchestrators import TektonOrchestrator

        return TektonOrchestrator
