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
"""DigitalOcean Container Registry (DOCR) flavor."""

from typing import Optional, Type

from pydantic import field_validator

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistryConfig,
    BaseContainerRegistryFlavor,
)
from zenml.integrations.digitalocean import (
    DIGITALOCEAN_CONTAINER_REGISTRY_FLAVOR,
)
from zenml.models import ServiceConnectorRequirements

DOCR_URI_PREFIX = "registry.digitalocean.com"


class DigitalOceanContainerRegistryConfig(BaseContainerRegistryConfig):
    """Configuration for the DigitalOcean Container Registry."""

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, uri: str) -> str:
        """Validates that the URI is a DigitalOcean Container Registry URI.

        Args:
            uri: URI to validate.

        Returns:
            The validated URI.

        Raises:
            ValueError: If the URI is not a valid DOCR URI.
        """
        # The inherited base validator has already stripped any trailing
        # slash. Require the exact DOCR host followed by a registry name: a
        # bare `startswith` would accept lookalike hosts such as
        # `registry.digitalocean.com.evil.example`, and a bare host without a
        # registry name is not a valid image push target.
        prefix = f"{DOCR_URI_PREFIX}/"
        if not uri.startswith(prefix) or not uri[len(prefix) :]:
            raise ValueError(
                f"Property `uri` for the DigitalOcean container registry must "
                f"be the DOCR host followed by your registry name. An example "
                f"of a valid URI is `{DOCR_URI_PREFIX}/my-registry`."
            )
        return uri


class DigitalOceanContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """DigitalOcean Container Registry (DOCR) flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DIGITALOCEAN_CONTAINER_REGISTRY_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "DigitalOcean"

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor. Any
        connector that provides a Docker registry resource can be used; a
        dedicated DigitalOcean service connector is a planned follow-up.

        Returns:
            Requirements for compatible service connectors.
        """
        return ServiceConnectorRequirements(
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            resource_id_attr="uri",
        )

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/digitalocean.png"

    @property
    def config_class(self) -> Type[DigitalOceanContainerRegistryConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return DigitalOceanContainerRegistryConfig
