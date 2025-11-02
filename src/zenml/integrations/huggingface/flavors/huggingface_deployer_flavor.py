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

if TYPE_CHECKING:
    from zenml.integrations.huggingface.deployers import HuggingfaceDeployer


class HuggingfaceDeployerConfig(BaseDeployerConfig):
    """Configuration for the Huggingface deployer.

    Attributes:
        token: Huggingface API token for authentication. If not provided,
            will attempt to use token from the Huggingface CLI login or
            from environment variables
        space_hardware: Hardware tier to use for the Space. Examples: 'cpu-basic',
            'cpu-upgrade', 't4-small', 't4-medium', 'a10g-small', 'a10g-large'.
            Defaults to 'cpu-basic' for free tier
        space_storage: Persistent storage tier for the Space. Options: 'small',
            'medium', 'large'. If not specified, uses ephemeral storage which
            resets on Space restart
        space_prefix: Prefix to use for Space names to organize deployments.
            The final Space name will be '{space_prefix}-{deployment_name}'.
            Must be a valid Huggingface Space name component
    """

    token: Optional[str] = None
    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None
    space_prefix: str = "zenml"


class HuggingfaceDeployerFlavor(BaseDeployerFlavor):
    """Flavor for the Huggingface deployer."""

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
        """Returns `HuggingfaceDeployerConfig` config class.

        Returns:
            The config class.
        """
        return HuggingfaceDeployerConfig

    @property
    def implementation_class(self) -> Type["HuggingfaceDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.huggingface.deployers import (
            HuggingfaceDeployer,
        )

        return HuggingfaceDeployer

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for this flavor.

        Returns:
            Service connector resource requirements.
        """
        return None
