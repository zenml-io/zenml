#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Docker Service Connector.

The Docker Service Connector is responsible for authenticating with a Docker
(or compatible) registry.
"""

import re
import subprocess
from typing import Any, List, Optional

from docker.client import DockerClient
from docker.errors import DockerException
from pydantic import Field, SecretStr

from zenml.constants import DOCKER_REGISTRY_RESOURCE_TYPE
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils import docker_utils
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class DockerCredentials(AuthenticationConfig):
    """Docker client authentication credentials."""

    username: SecretStr = Field(
        title="Username",
    )
    password: SecretStr = Field(
        title="Password",
    )


class DockerConfiguration(DockerCredentials):
    """Docker client configuration."""

    registry: Optional[str] = Field(
        default=None,
        title="Registry server URL. Omit to use DockerHub.",
    )


DOCKER_CONNECTOR_TYPE = "docker"
DOCKER_REGISTRY_NAME = "docker.io"


class DockerAuthenticationMethods(StrEnum):
    """Docker Authentication methods."""

    PASSWORD = "password"


DOCKER_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Docker Service Connector",
    connector_type=DOCKER_CONNECTOR_TYPE,
    description="""
The ZenML Docker Service Connector allows authenticating with a Docker or OCI
container registry and managing Docker clients for the registry. 

This connector provides pre-authenticated python-docker Python clients to Stack
Components that are linked to it.

No Python packages are required for this Service Connector. All prerequisites
are included in the base ZenML Python package. Docker needs to be installed on
environments where container images are built and pushed to the target container
registry.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
    emoji=":whale:",
    auth_methods=[
        AuthenticationMethodModel(
            name="Docker username and password/token",
            auth_method=DockerAuthenticationMethods.PASSWORD,
            description="""
Use a username and password or access token to authenticate with a container
registry server.
""",
            config_class=DockerConfiguration,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Docker/OCI container registry",
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            description="""
Allows users to access a Docker or OCI compatible container registry as a
resource. When used by connector consumers, they are provided a
pre-authenticated python-docker client instance.

The resource name identifies a Docker/OCI registry using one of the following
formats (the repository name is optional).
            
- DockerHub: docker.io or [https://]index.docker.io/v1/[/<repository-name>]
- generic OCI registry URI: http[s]://host[:port][/<repository-name>]
""",
            auth_methods=DockerAuthenticationMethods.values(),
            # Request a Docker repository to be configured in the
            # connector or provided by the consumer.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
            emoji=":whale:",
        ),
    ],
)


class DockerServiceConnector(ServiceConnector):
    """Docker service connector."""

    config: DockerConfiguration

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector specification.

        Returns:
            The service connector specification.
        """
        return DOCKER_SERVICE_CONNECTOR_TYPE_SPEC

    @classmethod
    def _parse_resource_id(
        cls,
        resource_id: str,
    ) -> str:
        """Validate and convert a Docker resource ID into a Docker registry name.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The Docker registry name.

        Raises:
            ValueError: If the provided resource ID is not a valid Docker
                registry.
        """
        registry: Optional[str] = None
        if re.match(
            r"^(https?://)?[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:[0-9]+)?(/.+)*$",
            resource_id,
        ):
            # The resource ID is a repository URL
            if resource_id.startswith("https://") or resource_id.startswith(
                "http://"
            ):
                registry = resource_id.split("/")[2]
            else:
                registry = resource_id.split("/")[0]
        else:
            raise ValueError(
                f"Invalid resource ID for a Docker registry: {resource_id}. "
                f"Please provide a valid repository name or URL in the "
                f"following format:\n"
                "DockerHub: docker.io or [https://]index.docker.io/v1/[/<repository-name>]"
                "generic OCI registry URI: http[s]://host[:port][/<repository-name>]"
            )

        if registry == f"index.{DOCKER_REGISTRY_NAME}":
            registry = DOCKER_REGISTRY_NAME
        return registry

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Convert a resource ID to its canonical form.

        Args:
            resource_type: The resource type to canonicalize.
            resource_id: The resource ID to canonicalize.

        Returns:
            The canonical resource ID.
        """
        return self._parse_resource_id(resource_id)

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Returns:
            The default resource ID for the resource type.
        """
        return self._canonical_resource_id(
            resource_type, self.config.registry or DOCKER_REGISTRY_NAME
        )

    def _authorize_client(
        self,
        docker_client: DockerClient,
        resource_id: str,
    ) -> None:
        """Authorize a Docker client to have access to the configured Docker registry.

        Args:
            docker_client: The Docker client to authenticate.
            resource_id: The resource ID to authorize the client for.

        Raises:
            AuthorizationException: If the client could not be authenticated.
        """
        cfg = self.config
        registry = self._parse_resource_id(resource_id)

        try:
            docker_client.login(
                username=cfg.username.get_secret_value(),
                password=cfg.password.get_secret_value(),
                registry=registry
                if registry != DOCKER_REGISTRY_NAME
                else None,
                reauth=True,
            )
        except DockerException as e:
            raise AuthorizationException(
                f"failed to authenticate with Docker registry {registry}: {e}"
            )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a Docker/OCI registry.

        Initialize, authenticate and return a python-docker client.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            An authenticated python-docker client object.
        """
        assert self.resource_id is not None

        docker_client = docker_utils._try_get_docker_client_from_env()

        self._authorize_client(docker_client, self.resource_id)

        return docker_client

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure the local Docker client to authenticate to a Docker/OCI registry.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
        """
        # Call the docker CLI to authenticate to the Docker registry
        cfg = self.config

        assert self.resource_id is not None
        registry = self._parse_resource_id(self.resource_id)

        docker_login_cmd = [
            "docker",
            "login",
            "-u",
            cfg.username.get_secret_value(),
            "--password-stdin",
        ]
        if registry != DOCKER_REGISTRY_NAME:
            docker_login_cmd.append(registry)

        try:
            subprocess.run(
                docker_login_cmd,
                check=True,
                input=cfg.password.get_secret_value().encode(),
            )
        except subprocess.CalledProcessError as e:
            raise AuthorizationException(
                f"Failed to authenticate to Docker registry "
                f"'{self.resource_id}': {e}"
            ) from e

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "DockerServiceConnector":
        """Auto-configure the connector.

        Not supported by the Docker connector.

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an resource type that
                supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Raises:
            NotImplementedError: If the connector auto-configuration fails or
                is not supported.
        """
        raise NotImplementedError(
            "Auto-configuration is not supported by the Docker connector."
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify that the connector can authenticate and access resources.

        Args:
            resource_type: The type of resource to verify. Must be set to the
                Docker resource type.
            resource_id: The Docker registry name or URL to connect to.

        Returns:
            The name of the Docker registry that this connector can access.
        """
        # The docker server isn't available on the ZenML server, so we can't
        # verify the credentials there.
        try:
            docker_client = DockerClient.from_env()
        except DockerException as e:
            logger.warning(
                f"Failed to connect to Docker daemon: {e}"
                f"\nSkipping Docker connector verification."
            )
        else:
            assert resource_id is not None
            self._authorize_client(docker_client, resource_id)
            docker_client.close()

        return [resource_id] if resource_id else []
