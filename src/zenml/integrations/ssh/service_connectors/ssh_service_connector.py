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
"""SSH service connector."""

from typing import Any, List, Optional

from pydantic import Field

from zenml.exceptions import AuthorizationException
from zenml.integrations.ssh import SSH_CONNECTOR_TYPE, SSH_HOST_RESOURCE_TYPE
from zenml.integrations.ssh.ssh_utils import SSHClient, SSHConnectionConfig
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


class SSHPrivateKeyCredentials(AuthenticationConfig):
    """SSH private-key credentials."""

    ssh_private_key: PlainSerializedSecretStr = Field(
        title="SSH private key",
    )
    ssh_key_passphrase: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="SSH private key passphrase",
    )


class SSHHostConfiguration(SSHPrivateKeyCredentials):
    """SSH host connection configuration."""

    hostnames: List[str] = Field(
        title="Hostnames of the supported SSH hosts",
    )
    username: str = Field(
        title="SSH username",
    )
    port: int = Field(
        default=22,
        ge=1,
        le=65535,
        title="SSH port",
    )
    verify_host_key: bool = Field(
        default=True,
        title="Verify SSH host key",
    )
    known_hosts_path: Optional[str] = Field(
        default=None,
        title="Known hosts path",
    )
    connection_timeout: float = Field(
        default=10.0,
        gt=0,
        title="Connection timeout in seconds",
    )
    keepalive_interval: int = Field(
        default=30,
        ge=0,
        title="Keepalive interval in seconds",
    )


class SSHAuthenticationMethods(StrEnum):
    """SSH authentication methods."""

    PRIVATE_KEY = "private-key"


SSH_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="SSH Service Connector",
    connector_type=SSH_CONNECTOR_TYPE,
    description="""
The ZenML SSH Service Connector authenticates to generic remote Linux hosts
over SSH.

It can be linked to SSH stack components, such as the SSH orchestrator and SSH
step operator, so SSH credentials are stored once and reused by both
components. Consumers receive an SSHConnectionConfig that is executed through
ZenML's shared SSHClient wrapper.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/ssh.png",
    emoji=":computer:",
    auth_methods=[
        AuthenticationMethodModel(
            name="SSH private key",
            auth_method=SSHAuthenticationMethods.PRIVATE_KEY,
            description="""
Use an SSH private key to authenticate to one or more remote Linux hosts. The
key may be encrypted with a passphrase.
""",
            config_class=SSHHostConfiguration,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="SSH host",
            resource_type=SSH_HOST_RESOURCE_TYPE,
            description="""
Remote Linux host accessible over SSH. When used by connector consumers, they
receive an SSHConnectionConfig for ZenML's shared SSHClient wrapper.
""",
            auth_methods=SSHAuthenticationMethods.values(),
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/ssh.png",
            emoji=":computer:",
        ),
    ],
)


class SSHServiceConnector(ServiceConnector):
    """Service connector for generic SSH hosts."""

    config: SSHHostConfiguration

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the connector type specification.

        Returns:
            The connector type specification.
        """
        return SSH_SERVICE_CONNECTOR_TYPE_SPEC

    @staticmethod
    def _normalize_hostname(hostname: str) -> str:
        """Normalize hostnames used as resource IDs.

        Args:
            hostname: The hostname to normalize.

        Returns:
            The normalized hostname.
        """
        return hostname.strip()

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Canonicalize an SSH host resource ID.

        Args:
            resource_type: The resource type.
            resource_id: The resource ID.

        Returns:
            The canonical resource ID.
        """
        return self._normalize_hostname(resource_id)

    def _connection_config(self, hostname: str) -> SSHConnectionConfig:
        """Build the SSH connection config for one hostname.

        Args:
            hostname: The remote SSH host.

        Returns:
            The SSH connection config.
        """
        passphrase: Optional[str] = None
        if self.config.ssh_key_passphrase is not None:
            passphrase = self.config.ssh_key_passphrase.get_secret_value()

        return SSHConnectionConfig(
            hostname=hostname,
            port=self.config.port,
            username=self.config.username,
            ssh_private_key=self.config.ssh_private_key.get_secret_value(),
            ssh_key_passphrase=passphrase,
            verify_host_key=self.config.verify_host_key,
            known_hosts_path=self.config.known_hosts_path,
            connection_timeout=self.config.connection_timeout,
            keepalive_interval=self.config.keepalive_interval,
        )

    def _connect_to_resource(self, **kwargs: Any) -> SSHConnectionConfig:
        """Return an SSH connection config for the configured host.

        Args:
            kwargs: Additional implementation-specific keyword arguments.

        Returns:
            The SSH connection config.

        Raises:
            AuthorizationException: If no host resource is configured.
        """
        if self.resource_id is None:
            raise AuthorizationException(
                "No SSH host resource is configured on the connector."
            )

        return self._connection_config(self.resource_id)

    def _configure_local_client(self, **kwargs: Any) -> None:
        """Configure a local SSH client.

        Args:
            kwargs: Additional implementation-specific keyword arguments.

        Raises:
            NotImplementedError: Always, local SSH client configuration is not
                supported.
        """
        raise NotImplementedError(
            "Local SSH client configuration is not supported by the SSH "
            "service connector."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "SSHServiceConnector":
        """Auto-configure the connector.

        Args:
            auth_method: The authentication method.
            resource_type: The resource type.
            resource_id: The resource ID.
            kwargs: Additional implementation-specific keyword arguments.

        Raises:
            NotImplementedError: Always, auto-configuration is not supported.
        """
        raise NotImplementedError(
            "Auto-configuration is not supported by the SSH service connector."
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify that the connector can access SSH hosts.

        Args:
            resource_type: The resource type to verify.
            resource_id: Optional hostname to verify.

        Returns:
            The verified hostnames.

        Raises:
            AuthorizationException: If a host is not allowed or authentication
                fails.
        """
        if resource_id:
            hostname = self._normalize_hostname(resource_id)
            allowed_hostnames = {
                self._normalize_hostname(hostname)
                for hostname in self.config.hostnames
            }
            if hostname not in allowed_hostnames:
                raise AuthorizationException(
                    f"The supplied SSH hostname {hostname!r} is not in the "
                    f"configured hostnames: {self.config.hostnames}."
                )
            hostnames = [hostname]
        else:
            hostnames = [
                self._normalize_hostname(hostname)
                for hostname in self.config.hostnames
            ]

        for hostname in hostnames:
            try:
                with SSHClient(self._connection_config(hostname)):
                    pass
            except Exception as e:
                logger.error(
                    "Failed to connect to SSH host %s: %s", hostname, e
                )
                raise AuthorizationException(
                    f"Could not connect to SSH host {hostname!r}."
                ) from e

        return hostnames
