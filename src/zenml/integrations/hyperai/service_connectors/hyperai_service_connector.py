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

from zenml.constants import COMPUTE_INSTANCE_RESOURCE_TYPE
from zenml.exceptions import AuthorizationException
from zenml.integrations.hyperai import (
    HYPERAI_CONNECTOR_TYPE,
    HYPERAI_RESOURCE_TYPE,
)
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

logger = get_logger(__name__)


class HyperAICredentials(AuthenticationConfig):
    """HyperAI client authentication credentials."""

    rsa_ssh_key: SecretStr = Field(
        title="SSH key",
    )
    rsa_ssh_key_passphrase: Optional[SecretStr] = Field(
        default=None,
        title="SSH key passphrase",
    )


class HyperAIConfiguration(HyperAICredentials):
    """HyperAI client configuration."""

    ip_address: str = Field(
        title="IP address of the HyperAI instance.",
    )

    username: str = Field(
        title="Username to use to connect to the HyperAI instance.",
    )

class HyperAIAuthenticationMethods(StrEnum):
    """HyperAI Authentication methods."""

    KEY_OPTIONAL_PASSPHRASE = "key_optional_passphrase"


HYPERAI_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="HyperAI Service Connector",
    connector_type=HYPERAI_CONNECTOR_TYPE,
    description="""
The ZenML HyperAI Service Connector allows authenticating to HyperAI (hyperai.ai)
GPU equipped instances of their Dedicated offering.

This connector provides an SSH connection to your HyperAI instance, which can be
used to run ZenML pipelines.

The connector requires a HyperAI Dedicated instance in order to work. The
instance must be configured to allow SSH connections from the ZenML server.
Docker and Docker Compose must be installed on the HyperAI instance.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/hyperai/hyperai.png",
    emoji=":robot_face:",
    auth_methods=[
        AuthenticationMethodModel(
            name="SSH key with optional passphrase",
            auth_method=HyperAIAuthenticationMethods.KEY_OPTIONAL_PASSPHRASE,
            description="""
Use an SSH key to authenticate with a HyperAI instance. The key may be
encrypted with a passphrase. If the key is encrypted, the passphrase must be
provided.
""",
            config_class=HyperAIConfiguration,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="HyperAI instance",
            resource_type=COMPUTE_INSTANCE_RESOURCE_TYPE,
            description="""
Allows users to access a HyperAI instance as a resource. When used by
connector consumers, they are provided a pre-authenticated SSH client
instance.
""",
            auth_methods=HyperAIAuthenticationMethods.values(),
            # Request a Docker repository to be configured in the
            # connector or provided by the consumer.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/hyperai/hyperai.png",
            emoji=":robot_face:",
        ),
    ],
)


class HyperAIServiceConnector(ServiceConnector):
    """HyperAI service connector."""

    config: HyperAIConfiguration

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector specification.

        Returns:
            The service connector specification.
        """
        return HYPERAI_SERVICE_CONNECTOR_TYPE_SPEC

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
        """Connect to a HyperAI instance. Returns an authenticated SSH client.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            An authenticated Paramiko SSH client.
        """
        assert self.resource_id is not None

        rsa_ssh_key = paramiko.RSAKey.from_private_key(
            io.StringIO(self.config.rsa_ssh_key.get_secret_value()),
            password=self.config.rsa_ssh_key_passphrase.get_secret_value(),
        )

        paramiko_client = paramiko.client.SSHClient()
        paramiko_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko_client.connect(
            hostname=self.config.ip_address,
            username=self.config.username,
            pkey=rsa_ssh_key,
            timeout=30
        )

        return paramiko_client

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
