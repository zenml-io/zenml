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

from pydantic import Field

from zenml.deployers.base_deployer import (
    BaseDeployerConfig,
    BaseDeployerFlavor,
    BaseDeployerSettings,
)
from zenml.integrations.huggingface import HUGGINGFACE_DEPLOYER_FLAVOR
from zenml.models import ServiceConnectorRequirements
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.huggingface.deployers import HuggingFaceDeployer


class HuggingFaceDeployerSettings(BaseDeployerSettings):
    """Hugging Face deployer settings.

    Attributes:
        space_hardware: Hardware tier for the Space (e.g., 'cpu-basic', 't4-small')
        space_storage: Persistent storage tier (e.g., 'small', 'medium', 'large')
        private: Whether to create a private Space (default: True for security)
    """

    space_hardware: Optional[str] = Field(
        default=None,
        description="Hardware tier for Space execution. Controls compute resources "
        "available to the deployed pipeline. Options: 'cpu-basic' (2 vCPU, 16GB RAM), "
        "'cpu-upgrade' (8 vCPU, 32GB RAM), 't4-small' (4 vCPU, 15GB RAM, NVIDIA T4), "
        "'t4-medium' (8 vCPU, 30GB RAM, NVIDIA T4). See "
        "https://huggingface.co/docs/hub/spaces-gpus for full list. Defaults to "
        "cpu-basic if not specified",
    )
    space_storage: Optional[str] = Field(
        default=None,
        description="Persistent storage tier for Space data. Determines available disk "
        "space for artifacts and logs. Options: 'small' (20GB), 'medium' (150GB), "
        "'large' (1TB). Storage persists across Space restarts. If not specified, "
        "uses ephemeral storage that resets on restart",
    )
    private: bool = Field(
        default=True,
        description="Controls whether the deployed Space is private or public. "
        "Private Spaces are only accessible to the owner and authorized users. "
        "Public Spaces are visible to anyone with the URL. Defaults to True for security",
    )


class HuggingFaceDeployerConfig(
    BaseDeployerConfig, HuggingFaceDeployerSettings
):
    """Configuration for the Hugging Face deployer."""

    token: Optional[str] = SecretField(
        default=None,
        description="Hugging Face API token for authentication with write permissions. "
        "Can reference a ZenML secret using {{secret_name.key}} syntax or provide "
        "the token directly. Create tokens at https://huggingface.co/settings/tokens "
        "with 'write' access enabled. Example: '{{hf_token.token}}' references the "
        "'token' key in the 'hf_token' secret",
    )
    organization: Optional[str] = Field(
        default=None,
        description="Hugging Face organization name to deploy Spaces under. If not "
        "specified, Spaces are created under the authenticated user's account. "
        "Example: 'zenml' deploys to https://huggingface.co/spaces/zenml/. "
        "Requires organization membership with appropriate permissions",
    )
    space_prefix: str = Field(
        default="zenml",
        description="Prefix for Space names to organize deployments and avoid naming "
        "conflicts. Combined with deployment name to form the full Space ID. "
        "Example: prefix 'zenml' with deployment 'my-pipeline' creates Space "
        "'zenml-my-pipeline'. Maximum combined length is 96 characters",
    )


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
