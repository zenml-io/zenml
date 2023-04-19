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
from typing import Any, Optional

from botocore.exceptions import ClientError
from pydantic import SecretStr

from zenml.exceptions import AuthorizationException
from zenml.models import (
    AuthenticationMethodSpecificationModel,
    ResourceTypeSpecificationModel,
    ServiceConnectorSpecificationModel,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum


class DockerCredentials(AuthenticationConfig):
    """Docker client authentication credentials."""

    username: SecretStr
    password: SecretStr


DOCKER_RESOURCE_TYPE = "docker"
DOCKER_CONNECTOR_TYPE = "docker"
DOCKER_RESOURCE_TYPE = "docker"


class DockerAuthenticationMethods(StrEnum):
    """AWS Authentication methods."""

    PASSWORD = "password"


DOCKER_SERVICE_CONNECTOR_SPECIFICATION = ServiceConnectorSpecificationModel(
    name="Docker Service Connector",
    type=DOCKER_CONNECTOR_TYPE,
    description="""
The ZenML Docker Service Connector allows authenticating with a Docker or OCI
container registry and managing Docker clients for the registry. 

The connector provides pre-authenticated python-docker clients.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
    auth_methods=[
        AuthenticationMethodSpecificationModel(
            name="Docker username and password",
            auth_method=DockerAuthenticationMethods.PASSWORD,
            description="""
Use a username and password or token to authenticate with a Docker registry.
""",
            config_class=DockerCredentials,
        ),
    ],
    resource_types=[
        ResourceTypeSpecificationModel(
            name="Docker/OCI container registry",
            resource_types=[DOCKER_RESOURCE_TYPE],
            description="""
Allows users to access a Docker or OCI container registry as a resource.
When used by connector consumers, they are provided a pre-authenticated
python-docker client instance.

The resource ID must identify a Docker/OCI repository using one of the following
formats:
            
- repository URI: http[s]://host[:port][/repository-name]
- DockerHub repository name: repository-name
""",
            auth_methods=DockerAuthenticationMethods.values(),
            # Request a Docker repository to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
        ),
    ],
)


class DockerServiceConnector(ServiceConnector):
    """Docker service connector."""

    config: DockerCredentials

    @classmethod
    def get_specification(cls) -> ServiceConnectorSpecificationModel:
        """Get the service connector specification.

        Returns:
            The service connector specification.
        """
        return DOCKER_SERVICE_CONNECTOR_SPECIFICATION

    @classmethod
    def _parse_resource_id(
        cls,
        resource_id: str,
    ) -> str:
        """Validate and convert a Docker resource ID into a Docker registry URL.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The Docker registry URL.

        Raises:
            ValueError: If the provided resource ID is not a valid Docker
                registry URL.
        """
        registry_url: Optional[str] = None
        if re.match(
            r"^http[s]?://[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:[0-9]+)?(/.*)*$",
            resource_id,
        ):
            # The resource ID is a repository URL
            registry_url = resource_id.split("/")[0]
        elif re.match(r"^([a-zA-Z0-9-]+(/.*)?)?$", resource_id):
            # The resource ID is a DockerHub repository name
            registry_url = ""
        else:
            raise ValueError(
                f"Invalid resource ID for a Docker registry: {resource_id}. "
                f"Please provide a valid repository name or URL in the "
                f"following format: "
                f" - repository URL: http[s://host[:port][/repository-name]"
                f" - DockerHub repository name: repository-name"
            )

        return registry_url

    def _connect_to_resource(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a Docker/OCI registry.

        Initialize and return a python-docker client.

        Args:
            resource_type: The type of resource to connect to.
            resource_id: The ID of the AWS resource to connect to.
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            An authenticated python-docker client object.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the indicated resource type or client type.
        """
        # Regardless of the resource type, we must authenticate to AWS first
        # before we can connect to any AWS resource
        auth_method = self.auth_method
        cfg = self.config
        resource_type = resource_type or self.resource_type

        if auth_method == DockerAuthenticationMethods.PASSWORD:
            assert isinstance(cfg, DockerCredentials)
        else:
            raise NotImplementedError(
                f"Authentication method '{auth_method}' is not supported by "
                "the Docker connector."
            )

        if resource_type == DOCKER_RESOURCE_TYPE:
            from docker import DockerClient

            resource_id = resource_id or self.resource_id
            if not resource_id:
                raise ValueError(
                    "The Docker connector was not configured with a Docker "
                    "registry and one was not provided at runtime."
                )

            registry_url = self._parse_resource_id(resource_id)

            docker_client = DockerClient.from_env()
            docker_client.login(
                username=cfg.username.get_secret_value(),
                password=cfg.password.get_secret_value(),
                registry=registry_url,
                reauth=True,
            )
            return docker_client

        raise NotImplementedError(
            f"Connecting to resource type '{resource_type}' is not supported "
            "by the Docker connector."
        )

    def _configure_local_client(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure the local Docker client to authenticate to a Docker/OCI registry.

        Args:
            resource_type: The type of resource to connect to. The only
                supported value is "docker".
            resource_id: The Docker registry name or URL to connect to.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the indicated resource type or client
                type.
        """
        # Call the docker CLI to authenticate to the Docker registry
        auth_method = self.auth_method
        cfg = self.config
        resource_type = resource_type or self.resource_type

        if auth_method == DockerAuthenticationMethods.PASSWORD:
            assert isinstance(cfg, DockerCredentials)
        else:
            raise NotImplementedError(
                f"Authentication method '{auth_method}' is not supported by "
                "the Docker connector."
            )

        if resource_type == DOCKER_RESOURCE_TYPE:
            resource_id = resource_id or self.resource_id
            if not resource_id:
                raise ValueError(
                    "The Docker connector was not configured with a Docker "
                    "registry and one was not provided at runtime."
                )

            registry_url = self._parse_resource_id(resource_id)
            docker_login_cmd = [
                "docker",
                "login",
                "-u",
                cfg.username.get_secret_value(),
                "--password-stdin",
                registry_url,
            ]
            try:
                subprocess.run(
                    docker_login_cmd,
                    check=True,
                    input=cfg.password.get_secret_value().encode(),
                )
            except subprocess.CalledProcessError as e:
                raise AuthorizationException(
                    f"Failed to authenticate to Docker registry "
                    f"{registry_url}': {e}"
                ) from e

        else:
            raise NotImplementedError(
                f"Resource type '{resource_type}' is not supported by the "
                "Docker connector."
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
            resource_type: The type of resource to configure. The implementation
                may choose to either require or ignore this parameter if it
                does not support or is able to detect a resource type and the
                connector specification does not allow arbitrary resource types.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an resource type that
                supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A connector instance configured with authentication credentials
            automatically extracted from the environment.

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
    ) -> None:
        """Verify that the connector can authenticate and connect.

        Args:
            resource_type: The type of resource to connect to. Can be different
                than the resource type that the connector is configured to
                access if alternative resource types or arbitrary
                resource types are allowed by the connector configuration.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured resource type does not allow multiple instances.
                Can be different than the resource ID that the connector is
                configured to access if resource ID aliases or wildcards
                are supported.
        """
        resource_type = resource_type or self.resource_type
        resource_id = resource_id or self.resource_id
        client = self._connect_to_resource(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == DOCKER_RESOURCE_TYPE:
            from docker import DockerClient

            assert isinstance(client, DockerClient)

            # Verify that the Docker registry exists and is accessible
            try:
                client.ping()
            except ClientError as err:
                raise AuthorizationException(
                    f"failed to verify Docker registry access: {err}"
                ) from err
