#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Huggingface deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
)
from zenml.integrations.huggingface import HUGGINGFACE_DEPLOYER_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.huggingface.deployers import HuggingFaceDeployer


class HuggingFaceDeployerConfig(BaseDeployerConfig):
    """Configuration for the Hugging Face deployer.

    Attributes:
        token: Hugging Face API token for authentication. Can be a direct token
            value or a reference to a ZenML secret using {{secret_name.key}}
        organization: HF organization to deploy to (uses username if not set)
        space_hardware: Hardware tier (e.g., 'cpu-basic', 't4-small')
        space_storage: Persistent storage tier (e.g., 'small', 'medium', 'large')
        space_prefix: Prefix for Space names to organize deployments
    """

    token: Optional[str] = SecretField(default=None)
    organization: Optional[str] = None
    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None
    space_prefix: str = "zenml"


class HuggingFaceDeployerFlavor(BaseDeployerFlavor):
    """Flavor for the Hugging Face deployer."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The flavor name.
        """
        return HUGGINGFACE_DEPLOYER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/deployer/huggingface.png"

    @property
    def config_class(self) -> Type[BaseDeployerConfig]:
        """Returns `HuggingFaceDeployerConfig` config class.

        Returns:
            The config class.
        """
        return HuggingFaceDeployerConfig

    @property
    def implementation_class(self) -> Type["HuggingFaceDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.huggingface.deployers import (
            HuggingFaceDeployer,
        )

        return HuggingFaceDeployer

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for this flavor.

        Returns:
            Service connector resource requirements.
        """
        return None
