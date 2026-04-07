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

import os
import re
from typing import Any, List, Optional

from pydantic import Field

from zenml.constants import (
    DOCKER_REGISTRY_RESOURCE_TYPE,
    DOCKERHUB_REGISTRY_URI,
    ENV_ZENML_SERVER,
)
from zenml.container_engines import get_container_engine
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
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import PlainSerializedSecretStr

logger = get_logger(__name__)


class DockerCredentials(AuthenticationConfig):
    """Docker client authentication credentials."""

    username: PlainSerializedSecretStr = Field(
        title="Username",
    )
    password: PlainSerializedSecretStr = Field(
        title="Password",
    )


class DockerConfiguration(DockerCredentials):
    """Docker client configuration."""

    registry: Optional[str] = Field(
        default=None,
        title="Registry server URL. Omit to use DockerHub.",
    )


DOCKER_CONNECTOR_TYPE = "docker"


class DockerAuthenticationMethods(StrEnum):
    """Docker Authentication methods."""

    PASSWORD = "password"


DOCKER_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Docker Service Connector",
    connector_type=DOCKER_CONNECTOR_TYPE,
    description="""
The ZenML Docker Service Connector authenticates to a Docker or OCI container
registry. Connecting logs the active engine into that registry,
then returns a reusable container engine (Docker or Podman, following global
ZenML configuration) for linked stack components.

No extra Python packages are required beyond the base ZenML install. Install
Docker or Podman on machines that build or push images to the registry.
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
resource. When used by connector consumers, the connector performs registry
login and provides a container engine instance.

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

        if registry == f"index.{DOCKERHUB_REGISTRY_URI}":
            registry = DOCKERHUB_REGISTRY_URI
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
            resource_type,
            self.config.registry or DOCKERHUB_REGISTRY_URI,
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and return a container engine for this registry.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            Any: Authenticated container engine for the registry.
        """
        assert self.resource_id is not None

        registry = self._parse_resource_id(self.resource_id)

        container_engines = get_container_engine()
        container_engines.login(
            username=self.config.username.get_secret_value(),
            password=self.config.password.get_secret_value(),
            registry=registry,
        )
        return container_engines

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Log the active container engine into the registry via CLI config.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.
        """
        cfg = self.config

        assert self.resource_id is not None
        registry = self._parse_resource_id(self.resource_id)

        container_engines = get_container_engine()
        container_engines.login(
            username=cfg.username.get_secret_value(),
            password=cfg.password.get_secret_value(),
            registry=registry,
        )

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

        Raises:
            RuntimeError: If the container engine is unavailable during
                verification on a non-server client.
        """
        # The docker server isn't available on the ZenML server, so we can't
        # verify the credentials there.
        if ENV_ZENML_SERVER not in os.environ:
            engine = get_container_engine()
            is_available, error_message = engine.check_availability()
            if not is_available:
                raise RuntimeError(
                    f"The container engine is not available: {error_message}"
                )

        return [resource_id] if resource_id else []
