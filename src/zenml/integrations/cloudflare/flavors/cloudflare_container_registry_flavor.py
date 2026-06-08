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
"""Cloudflare container registry flavor."""

from typing import Optional

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryFlavor,
)
from zenml.integrations.cloudflare import (
    CLOUDFLARE_CONTAINER_REGISTRY_FLAVOR,
)


class CloudflareContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """Flavor for the Cloudflare managed container registry.

    The Cloudflare container registry is a standard Docker registry hosted at
    ``registry.cloudflare.com``. Images are namespaced by account, so the
    configured `uri` is typically
    ``registry.cloudflare.com/<account_id>``.
    """

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return CLOUDFLARE_CONTAINER_REGISTRY_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Cloudflare"

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/cloudflare.png"
