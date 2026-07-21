#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""vLLM Kubernetes model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.enums import KubernetesServiceType
from zenml.integrations.vllm import VLLM_KUBERNETES_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.models import ServiceConnectorRequirements
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.vllm.model_deployers import (
        KubernetesVLLMModelDeployer,
    )

DEFAULT_VLLM_IMAGE = "vllm/vllm-openai:v0.25.1"


class KubernetesVLLMModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the Kubernetes vLLM model deployer.

    Attributes:
        kubernetes_context: name of a Kubernetes context to deploy vLLM servers to. If the stack component is linked to a Kubernetes service connector, this field is ignored.
        kubernetes_namespace: default Kubernetes namespace for vLLM deployments. Can be overridden per-deployment on the service config.
        incluster: if `True`, connect using the Kubernetes configuration of the cluster the client itself is running in. Requires the client to run in a Kubernetes pod. If set, `kubernetes_context` is ignored.
        default_image: default vLLM server image used when a deployment doesn't specify one.
        default_service_type: default Kubernetes Service type used when a deployment doesn't specify one.
        hf_token: Hugging Face access token used to download gated models when a deployment doesn't configure its own token or existing secret.
    """

    kubernetes_context: Optional[str] = Field(
        default=None,
        description="Name of a Kubernetes context to deploy vLLM servers "
        "to. Ignored when the stack component is linked to a Kubernetes "
        "service connector",
    )
    kubernetes_namespace: str = Field(
        default="zenml-vllm",
        description="Kubernetes namespace in which vLLM deployment "
        "servers are provisioned and managed by ZenML",
    )
    incluster: bool = Field(
        default=False,
        description="Connect using the Kubernetes configuration of the "
        "cluster the client itself is running in. Requires the client to "
        "run inside a Kubernetes pod. When set, `kubernetes_context` is "
        "ignored",
    )
    default_image: str = Field(
        default=DEFAULT_VLLM_IMAGE,
        description="Container image used to run the vLLM OpenAI-"
        "compatible server when a deployment doesn't specify its own "
        "image",
    )
    default_service_type: KubernetesServiceType = Field(
        default=KubernetesServiceType.LOAD_BALANCER,
        description="Kubernetes Service type used to expose a vLLM "
        "deployment when a deployment doesn't specify its own service "
        "type",
    )
    hf_token: Optional[str] = SecretField(
        default=None,
        description="Hugging Face access token used to download gated "
        "models. Used as a fallback for deployments that configure "
        "neither their own token nor an existing Kubernetes secret",
    )


class KubernetesVLLMModelDeployerFlavor(BaseModelDeployerFlavor):
    """Kubernetes vLLM model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return VLLM_KUBERNETES_MODEL_DEPLOYER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/vllm.png"

    @property
    def config_class(self) -> Type[KubernetesVLLMModelDeployerConfig]:
        """Returns `KubernetesVLLMModelDeployerConfig` config class.

        Returns:
            The config class.
        """
        return KubernetesVLLMModelDeployerConfig

    @property
    def implementation_class(self) -> Type["KubernetesVLLMModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.vllm.model_deployers import (
            KubernetesVLLMModelDeployer,
        )

        return KubernetesVLLMModelDeployer
