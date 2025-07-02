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
"""Implementation of a DockerHub Container Registry class."""

from typing import Optional, Type

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
    BaseContainerRegistryFlavor,
)
from zenml.enums import ContainerRegistryFlavor
from zenml.models import ServiceConnectorRequirements


class DockerHubContainerRegistry(BaseContainerRegistry):
    """Container registry implementation for DockerHub."""

    @property
    def registry_server_uri(self) -> str:
        """Get the DockerHub registry server URI.

        DockerHub requires authentication against the specific
        'https://index.docker.io/v1/' endpoint regardless of how
        the registry URI is configured.

        Returns:
            The DockerHub registry server URI.
        """
        return "https://index.docker.io/v1/"


class DockerHubContainerRegistryFlavor(BaseContainerRegistryFlavor):
    """Class for DockerHub Container Registry."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return ContainerRegistryFlavor.DOCKERHUB.value

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
            connector_type="docker",
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            resource_id_attr="uri",
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png"

    @property
    def implementation_class(self) -> Type[DockerHubContainerRegistry]:
        """Implementation class for DockerHub container registry.

        Returns:
            The DockerHub container registry implementation class.
        """
        return DockerHubContainerRegistry
