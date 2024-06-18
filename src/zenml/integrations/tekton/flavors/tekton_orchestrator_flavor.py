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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import model_validator

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.tekton import TEKTON_ORCHESTRATOR_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.tekton.orchestrators import TektonOrchestrator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


class TektonOrchestratorSettings(BaseSettings):
    """Settings for the Tekton orchestrator.

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
    """

    synchronous: bool = True
    timeout: int = 1200

    client_args: Dict[str, Any] = {}
    client_username: Optional[str] = SecretField(default=None)
    client_password: Optional[str] = SecretField(default=None)
    user_namespace: Optional[str] = None
    node_selectors: Dict[str, str] = {}
    node_affinity: Dict[str, List[str]] = {}
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
        # Validate username and password for auth cookie logic
        username = data.get("client_username")
        password = data.get("client_password")
        client_creds_error = "`client_username` and `client_password` both need to be set together."
        if (username and password is None) or (password and username is None):
            raise ValueError(client_creds_error)
        return data


class TektonOrchestratorConfig(
    BaseOrchestratorConfig, TektonOrchestratorSettings
):
    """Configuration for the Tekton orchestrator.

    Attributes:
        tekton_hostname: Hostname of the Tekton server.
        kubernetes_context: Name of a kubernetes context to run
            pipelines in. If the stack component is linked to a Kubernetes
            service connector, this field is ignored. Otherwise, it is
            mandatory.
        kubernetes_namespace: Name of the kubernetes namespace in which the
            pods that run the pipeline steps should be running.
    """

    tekton_hostname: Optional[str] = None
    kubernetes_context: Optional[str] = None
    kubernetes_namespace: str = "kubeflow"

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
            "tekton_ui_port",
            "skip_ui_daemon_provisioning",
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/tekton.png"

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
