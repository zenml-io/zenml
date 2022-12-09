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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

from pydantic import root_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubeflow import KUBEFLOW_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator

logger = get_logger(__name__)

DEFAULT_KFP_UI_PORT = 8080


class KubeflowOrchestratorSettings(BaseSettings):
    """Settings for the Kubeflow orchestrator.

    Attributes:
        synchronous: If `True`, running a pipeline using this orchestrator will
            block until all steps finished running on KFP. This setting only
            has an effect when specified on the pipeline and will be ignored if
            specified on steps.
        timeout: How many seconds to wait for synchronous runs.
        client_args: Arguments to pass when initializing the KFP client.
        client_username: Username to generate a session cookie for the kubeflow client. Both `client_username`
        and `client_password` need to be set together.
        client_password: Password to generate a session cookie for the kubeflow client. Both `client_username`
        and `client_password` need to be set together.
        user_namespace: The user namespace to use when creating experiments
            and runs.
        node_selectors: Deprecated: Node selectors to apply to KFP pods.
        node_affinity: Deprecated: Node affinities to apply to KFP pods.
        pod_settings: Pod settings to apply.
    """

    synchronous: bool = False
    timeout: int = 1200

    client_args: Dict[str, Any] = {}
    client_username: Optional[str] = SecretField()
    client_password: Optional[str] = SecretField()
    user_namespace: Optional[str] = None
    node_selectors: Dict[str, str] = {}
    node_affinity: Dict[str, List[str]] = {}
    pod_settings: Optional[KubernetesPodSettings] = None

    @root_validator
    def _validate_and_migrate_pod_settings(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validates settings and migrates pod settings from older version.

        Args:
            values: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.

        Raises:
            AssertionError: If old and new settings are used together.
            ValueError: If username and password are not specified together.
        """
        has_pod_settings = bool(values.get("pod_settings"))

        node_selectors = cast(
            Dict[str, str], values.get("node_selectors") or {}
        )
        node_affinity = cast(
            Dict[str, List[str]], values.get("node_affinity") or {}
        )

        has_old_settings = any([node_selectors, node_affinity])

        if has_old_settings:
            logger.warning(
                "The attributes `node_selectors` and `node_affinity` of the "
                "Kubeflow settings will be deprecated soon. Use the "
                "attribute `pod_settings` instead.",
            )

        if has_pod_settings and has_old_settings:
            raise AssertionError(
                "Got Kubeflow pod settings using both the deprecated "
                "attributes `node_selectors` and `node_affinity` as well as "
                "the new attribute `pod_settings`. Please specify Kubeflow "
                "pod settings only using the new `pod_settings` attribute."
            )
        elif has_old_settings:
            from kubernetes import client as k8s_client

            affinity = {}
            if node_affinity:
                match_expressions = [
                    k8s_client.V1NodeSelectorRequirement(
                        key=key,
                        operator="In",
                        values=values,
                    )
                    for key, values in node_affinity.items()
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
            pod_settings = KubernetesPodSettings(
                node_selectors=node_selectors, affinity=affinity
            )
            values["pod_settings"] = pod_settings
            values["node_affinity"] = {}
            values["node_selectors"] = {}

        # Validate username and password for auth cookie logic
        username = values.get("client_username")
        password = values.get("client_password")
        client_creds_error = "`client_username` and `client_password` both need to be set together."
        if username and password is None:
            raise ValueError(client_creds_error)
        if password and username is None:
            raise ValueError(client_creds_error)

        return values


class KubeflowOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, KubeflowOrchestratorSettings
):
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
        skip_local_validations: If `True`, the local validations will be
            skipped.
        skip_cluster_provisioning: If `True`, the k3d cluster provisioning will
            be skipped.
        skip_ui_daemon_provisioning: If `True`, provisioning the KFP UI daemon
            will be skipped.
        container_registry_name: The name of the container registry stack
            component to use. If not specified, the container registry
            in the active stack is used.
    """

    kubeflow_pipelines_ui_port: int = DEFAULT_KFP_UI_PORT
    kubeflow_hostname: Optional[str] = None
    kubeflow_namespace: str = "kubeflow"
    kubernetes_context: Optional[str] = None  # TODO: Potential setting
    skip_local_validations: bool = False
    skip_cluster_provisioning: bool = False
    skip_ui_daemon_provisioning: bool = False

    # IMPORTANT: This is a temporary solution to allow the Kubeflow orchestrator
    # to be provisioned as an individual component (i.e. same as running
    # `zenml orchestrator kubeflow up`) rather than needing it to be part of the
    # active stack (i.e. instead of running `zenml stack up`). This is required
    # by the test framework because the way it works is that it first provisions
    # the stack components individually, then each test gets a different stack
    # with the components it requires.
    # Do not use for anything else! This will be removed in the near future.
    container_registry_name: Optional[str] = None

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
