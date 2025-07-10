#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Kubernetes step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubernetes import KUBERNETES_STEP_OPERATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.step_operators import (
        KubernetesStepOperator,
    )


class KubernetesStepOperatorSettings(BaseSettings):
    """Settings for the Kubernetes step operator.

    Configuration options for individual step execution on Kubernetes.
    Field descriptions are defined inline using Field() descriptors.
    """

    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod configuration for step execution containers.",
    )
    service_account_name: Optional[str] = Field(
        default=None,
        description="Kubernetes service account for step pods. Uses default account if not specified.",
    )
    privileged: bool = Field(
        default=False,
        description="Whether to run step containers in privileged mode with extended permissions.",
    )
    pod_startup_timeout: int = Field(
        default=600,
        description="Maximum seconds to wait for step pods to start. Default is 10 minutes.",
    )
    pod_failure_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts when step pods fail to start.",
    )
    pod_failure_retry_delay: int = Field(
        default=10,
        description="Delay in seconds between pod failure retry attempts.",
    )
    pod_failure_backoff: float = Field(
        default=1.0,
        description="Exponential backoff factor for retry delays. Values > 1.0 increase delay with each retry.",
    )


class KubernetesStepOperatorConfig(
    BaseStepOperatorConfig, KubernetesStepOperatorSettings
):
    """Configuration for the Kubernetes step operator.

    Defines cluster connection and execution settings.
    Field descriptions are defined inline using Field() descriptors.
    """

    kubernetes_namespace: str = Field(
        default="zenml",
        description="Kubernetes namespace for step execution. Must be a valid namespace name.",
    )
    incluster: bool = Field(
        default=False,
        description="Whether to execute within the same cluster as the orchestrator. "
        "Requires appropriate pod creation permissions.",
    )
    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Kubernetes context name for cluster connection. "
        "Ignored when using service connectors or in-cluster execution.",
    )

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


class KubernetesStepOperatorFlavor(BaseStepOperatorFlavor):
    """Kubernetes step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBERNETES_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesStepOperatorConfig]:
        """Returns `KubernetesStepOperatorConfig` config class.

        Returns:
                The config class.
        """
        return KubernetesStepOperatorConfig

    @property
    def implementation_class(self) -> Type["KubernetesStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.step_operators import (
            KubernetesStepOperator,
        )

        return KubernetesStepOperator
