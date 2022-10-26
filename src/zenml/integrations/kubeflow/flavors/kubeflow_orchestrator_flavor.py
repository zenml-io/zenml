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
"""Kubeflow orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubeflow import KUBEFLOW_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator


DEFAULT_KFP_UI_PORT = 8080


class KubeflowOrchestratorSettings(BaseSettings):
    """Settings for the Kubeflow orchestrator.

    Attributes:
        client_args: Arguments to pass when initializing the KFP client.
        user_namespace: The user namespace to use when creating experiments
            and runs.
        node_selectors: Node selectors to apply to KFP pods.
        node_affinity: Node affinities to apply to KFP pods.
    """

    client_args: Dict[str, Any] = {}
    user_namespace: Optional[str] = None
    node_selectors: Dict[str, str] = {}
    node_affinity: Dict[str, List[str]] = {}


class KubeflowOrchestratorConfig(BaseOrchestratorConfig):
    """Configuration for the Kubeflow orchestrator.

    Attributes:
        kubeflow_pipelines_ui_port: A local port to which the KFP UI will be
            forwarded.
        kubeflow_hostname: The hostname to use to talk to the Kubeflow Pipelines
            API. If not set, the hostname will be derived from the Kubernetes
            API proxy.
        kubeflow_namespace: The Kubernetes namespace in which Kubeflow
            Pipelines is deployed. Defaults to `kubeflow`.
        kubernetes_context: Optional name of a kubernetes context to run
            pipelines in. If not set, will try to spin up a local K3d cluster.
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on KFP.
        skip_local_validations: If `True`, the local validations will be
            skipped.
        skip_cluster_provisioning: If `True`, the k3d cluster provisioning will
            be skipped.
        skip_ui_daemon_provisioning: If `True`, provisioning the KFP UI daemon
            will be skipped.
    """

    kubeflow_pipelines_ui_port: int = DEFAULT_KFP_UI_PORT
    kubeflow_hostname: Optional[str] = None
    kubeflow_namespace: str = "kubeflow"
    kubernetes_context: Optional[str] = None
    synchronous: bool = False
    skip_local_validations: bool = False
    skip_cluster_provisioning: bool = False
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
        if (
            self.kubernetes_context is not None
            and not self.kubernetes_context.startswith("k3d-zenml-kubeflow-")
        ):
            return True
        return False

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        if (
            self.kubernetes_context is None
            or self.kubernetes_context.startswith("k3d-zenml-kubeflow-")
        ):
            return True
        return False


class KubeflowOrchestratorFlavor(BaseOrchestratorFlavor):
    """Kubeflow orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBEFLOW_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[KubeflowOrchestratorConfig]:
        """Returns `KubeflowOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return KubeflowOrchestratorConfig

    @property
    def implementation_class(self) -> Type["KubeflowOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubeflow.orchestrators import (
            KubeflowOrchestrator,
        )

        return KubeflowOrchestrator
