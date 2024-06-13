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

from pydantic import model_validator

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubeflow import KUBEFLOW_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator

logger = get_logger(__name__)

DEFAULT_KFP_UI_PORT = 8080


class KubeflowOrchestratorSettings(BaseSettings):
    """Settings for the Kubeflow orchestrator.

    Attributes:
        synchronous: If `True`, the client running a pipeline using this
            orchestrator waits until all steps finish running. If `False`,
            the client returns immediately and the pipeline is executed
            asynchronously. Defaults to `True`. This setting only
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
        pod_settings: Pod settings to apply.
    """

    synchronous: bool = True
    timeout: int = 1200

    client_args: Dict[str, Any] = {}
    client_username: Optional[str] = SecretField(default=None)
    client_password: Optional[str] = SecretField(default=None)
    user_namespace: Optional[str] = None
    pod_settings: Optional[KubernetesPodSettings] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _validate_and_migrate_pod_settings(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validates settings and migrates pod settings from older version.

        Args:
            data: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.

        Raises:
            ValueError: If username and password are not specified together.
        """
        node_selectors = cast(Dict[str, str], data.get("node_selectors") or {})
        node_affinity = cast(
            Dict[str, List[str]], data.get("node_affinity") or {}
        )

        affinity = {}
        if node_affinity:
            from kubernetes import client as k8s_client

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
        data["pod_settings"] = pod_settings

        # Validate username and password for auth cookie logic
        username = data.get("client_username")
        password = data.get("client_password")
        client_creds_error = "`client_username` and `client_password` both need to be set together."
        if username and password is None:
            raise ValueError(client_creds_error)
        if password and username is None:
            raise ValueError(client_creds_error)

        return data


class KubeflowOrchestratorConfig(
    BaseOrchestratorConfig, KubeflowOrchestratorSettings
):
    """Configuration for the Kubeflow orchestrator.

    Attributes:
        kubeflow_hostname: The hostname to use to talk to the Kubeflow Pipelines
            API. If not set, the hostname will be derived from the Kubernetes
            API proxy. Mandatory when connecting to a multi-tenant Kubeflow
            Pipelines deployment.
        kubeflow_namespace: The Kubernetes namespace in which Kubeflow
            Pipelines is deployed. Defaults to `kubeflow`.
        kubernetes_context: Name of a kubernetes context to run
            pipelines in. Not applicable when connecting to a multi-tenant
            Kubeflow Pipelines deployment (i.e. when `kubeflow_hostname` is
            set) or if the stack component is linked to a Kubernetes service
            connector.
    """

    kubeflow_hostname: Optional[str] = None
    kubeflow_namespace: str = "kubeflow"
    kubernetes_context: Optional[str]  # TODO: Potential setting

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _validate_deprecated_attrs(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic root_validator for deprecated attributes.

        This root validator is used for backwards compatibility purposes. E.g.
        it handles attributes that are no longer available or that have become
        mandatory in the meantime.

        Args:
            data: Values passed to the object constructor

        Returns:
            Values passed to the object constructor
        """
        provisioning_attrs = [
            "skip_cluster_provisioning",
            "skip_ui_daemon_provisioning",
            "kubeflow_pipelines_ui_port",
        ]

        # remove deprecated attributes from values dict
        for attr in provisioning_attrs:
            if attr in data:
                del data[attr]

        return data

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

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous


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
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubeflow.png"

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
