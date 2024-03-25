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

from pydantic import field_validator

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.enums import StackComponentType
from zenml.models import ServiceConnectorRequirements
from zenml.secret.schemas import BasicAuthSecretSchema
from zenml.stack.authentication_mixin import (
    AuthenticationConfigMixin,
    AuthenticationMixin,
)
from zenml.stack.flavor import Flavor
from zenml.utils import docker_utils

if TYPE_CHECKING:
    from docker.client import DockerClient


class BaseContainerRegistryConfig(AuthenticationConfigMixin):
    """Base config for a container registry.

    Attributes:
        uri: The URI of the container registry.
    """

    uri: str

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

    _docker_client: Optional["DockerClient"] = None

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

        connector = self.get_connector()
        if connector:
            from zenml.service_connectors.docker_service_connector import (
                DockerServiceConnector,
            )

            if isinstance(connector, DockerServiceConnector):
                return (
                    connector.config.username.get_secret_value(),
                    connector.config.password.get_secret_value(),
                )

        return None

    @property
    def docker_client(self) -> "DockerClient":
        """Returns a Docker client for this container registry.

        Returns:
            The Docker client.

        Raises:
            RuntimeError: If the connector does not return a Docker client.
        """
        from docker.client import DockerClient

        # Refresh the client also if the connector has expired
        if self._docker_client and not self.connector_has_expired():
            return self._docker_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, DockerClient):
                raise RuntimeError(
                    f"Expected a DockerClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._docker_client = client
        else:
            self._docker_client = (
                docker_utils._try_get_docker_client_from_env()
            )

            credentials = self.credentials
            if credentials:
                username, password = credentials
                self._docker_client.login(
                    username=username,
                    password=password,
                    registry=self.config.uri,
                    reauth=True,
                )

        return self._docker_client

    def prepare_image_push(self, image_name: str) -> None:
        """Preparation before an image gets pushed.

        Subclasses can overwrite this to do any necessary checks or
        preparations before an image gets pushed.

        Args:
            image_name: Name of the docker image that will be pushed.
        """

    def push_image(self, image_name: str) -> str:
        """Pushes a docker image.

        Args:
            image_name: Name of the docker image that will be pushed.

        Returns:
            The Docker repository digest of the pushed image.

        Raises:
            ValueError: If the image name is not associated with this
                container registry.
        """
        if not image_name.startswith(self.config.uri):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{self.config.uri}`."
            )

        self.prepare_image_push(image_name)
        return docker_utils.push_image(
            image_name, docker_client=self.docker_client
        )


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
