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
"""Implementation of the GitHub Container Registry."""
from typing import Optional

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryConfig,
    BaseContainerRegistryFlavor,
)
from zenml.enums import ContainerRegistryFlavor


class GitHubContainerRegistryConfig(BaseContainerRegistryConfig):
    """Configuration for the GitHub Container Registry.

    Attributes:
        automatic_token_authentication: If `True`, use automatic token
            authentication (https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)
            when trying to access this container registry from within a GitHub
            Actions environment.
    """

    automatic_token_authentication: bool = False


class GitHubContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """Class for GitHub Container Registry."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return ContainerRegistryFlavor.GITHUB

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/github.png"
