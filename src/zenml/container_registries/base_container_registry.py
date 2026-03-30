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
"""Implementation of a base container registry class."""

import re
from typing import TYPE_CHECKING, Optional, Tuple, Type, cast

from pydantic import Field, field_validator

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.enums import StackComponentType
from zenml.models import ServiceConnectorRequirements
from zenml.secret.schemas import BasicAuthSecretSchema
from zenml.stack.authentication_mixin import (
    AuthenticationConfigMixin,
    AuthenticationMixin,
)
from zenml.stack.flavor import Flavor

if TYPE_CHECKING:
    pass


class BaseContainerRegistryConfig(AuthenticationConfigMixin):
    """Base config for a container registry.

    Configuration for connecting to container image registries.
    Field descriptions are defined inline using Field() descriptors.
    """

    uri: str = Field(
        description="Container registry URI (e.g., 'gcr.io' for Google Container "
        "Registry, 'docker.io' for Docker Hub, 'registry.gitlab.com' for GitLab "
        "Container Registry, 'ghcr.io' for GitHub Container Registry). This is "
        "the base URL where container images will be pushed to and pulled from."
    )
    default_repository: Optional[str] = Field(
        default=None,
        description="Default repository namespace for image storage (e.g., "
        "'username' for Docker Hub, 'project-id' for GCR, 'organization' for "
        "GitHub Container Registry). If not specified, images will be stored at "
        "the registry root. For Docker Hub this would mean only official images "
        "can be pushed.",
    )

    @field_validator("uri")
    @classmethod
    def strip_trailing_slash(cls, uri: str) -> str:
        """Removes trailing slashes from the URI.

        Args:
            uri: The URI to be stripped.

        Returns:
            The URI without trailing slashes.
        """
        return uri.rstrip("/")

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return bool(re.fullmatch(r"localhost:[0-9]{4,5}", self.uri))


class BaseContainerRegistry(AuthenticationMixin):
    """Base class for all ZenML container registries."""

    _credentials: Optional[Tuple[str, str]] = None

    @property
    def config(self) -> BaseContainerRegistryConfig:
        """Returns the `BaseContainerRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseContainerRegistryConfig, self._config)

    @property
    def requires_authentication(self) -> bool:
        """Returns whether the container registry requires authentication.

        Returns:
            `True` if the container registry requires authentication,
            `False` otherwise.
        """
        return bool(self.config.authentication_secret)

    @property
    def credentials(self) -> Optional[Tuple[str, str]]:
        """Username and password to authenticate with this container registry.

        Returns:
            Tuple with username and password if this container registry
            requires authentication, `None` otherwise.
        """
        secret = self.get_typed_authentication_secret(
            expected_schema_type=BasicAuthSecretSchema
        )
        if secret:
            return secret.username, secret.password

        # Refresh the credentials also if the connector has expired
        if self._credentials and not self.connector_has_expired():
            return self._credentials

        connector = self.get_connector()
        if connector:
            from zenml.service_connectors.docker_service_connector import (
                DockerServiceConnector,
            )

            if isinstance(connector, DockerServiceConnector):
                self._credentials = (
                    connector.config.username.get_secret_value(),
                    connector.config.password.get_secret_value(),
                )

                return self._credentials

        return None

    def is_valid_image_name_for_registry(self, image_name: str) -> bool:
        """Check if the image name is valid for the container registry.

        Args:
            image_name: The name of the image.

        Returns:
            `True` if the image name is valid for the container registry,
            `False` otherwise.
        """
        # Remove prefixes to make sure this logic also works for DockerHub
        image_name = image_name.removeprefix("index.docker.io/")
        image_name = image_name.removeprefix("docker.io/")

        registry_uri = self.config.uri.removeprefix("index.docker.io/")
        registry_uri = registry_uri.removeprefix("docker.io/")

        return image_name.startswith(registry_uri)

    def prepare_image_push(self, image_name: str) -> None:
        """Preparation before an image gets pushed.

        Subclasses can overwrite this to do any necessary checks or
        preparations before an image gets pushed.

        Args:
            image_name: Name of the docker image that will be pushed.
        """


class BaseContainerRegistryFlavor(Flavor):
    """Base flavor for container registries."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.CONTAINER_REGISTRY

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
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            resource_id_attr="uri",
        )

    @property
    def config_class(self) -> Type[BaseContainerRegistryConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return BaseContainerRegistryConfig

    @property
    def implementation_class(self) -> Type[BaseContainerRegistry]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return BaseContainerRegistry
