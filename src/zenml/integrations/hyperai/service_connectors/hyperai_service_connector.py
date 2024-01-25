#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""HyperAI Service Connector.

The HyperAI Service Connector allows authenticating to HyperAI (hyperai.ai)
GPU equipped instances of their Dedicated offering.
"""
import base64
import paramiko
import io
import re
import subprocess
from typing import Any, List, Optional

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
        title="SSH key (base64)",
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

    instance_name: Optional[str] = Field(
        default=None,
        title="Name to identify the HyperAI instance, if any.",
    )

    username: str = Field(
        title="Username to use to connect to the HyperAI instance.",
    )

class HyperAIAuthenticationMethods(StrEnum):
    """HyperAI Authentication methods."""

    KEY_OPTIONAL_PASSPHRASE = "ssh-key"


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

    # def _canonical_resource_id(
    #     self, resource_type: str, resource_id: str
    # ) -> str:
    #     """Convert a resource ID to its canonical form.

    #     Args:
    #         resource_type: The resource type to canonicalize.
    #         resource_id: The resource ID to canonicalize.

    #     Returns:
    #         The canonical resource ID.
    #     """
    #     return self._parse_resource_id(resource_id)

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Returns:
            The default resource ID for the resource type.
        """
        instance_name = self.config.instance_name
        if instance_name is None:
            instance_name = "Unnamed instance"

        return f"{instance_name} (IP {self.config.ip_address})"

    def _authorize_client(
        self
    ) -> None:
        """Verify that the client can authenticate with the HyperAI instance.

        Raises:
            BadHostKeyException: If the host key is invalid.
            AuthenticationException: If the authentication credentials are
                invalid.
            SSHException: If there is an SSH related error.
        """
        if self.config.rsa_ssh_key_passphrase is None:
            rsa_ssh_key_passphrase = None
        else:
            rsa_ssh_key_passphrase = self.config.rsa_ssh_key_passphrase.get_secret_value()

        # Convert the SSH key from base64 to string
        base64_key_value = self.config.rsa_ssh_key.get_secret_value()
        try:
            ssh_key = base64.b64decode(base64_key_value).decode("utf-8")
        except Exception as e:
            logger.error("Failed to decode SSH key from Base64 format: %s", e)
        
        # Attempt constructing an RSA key from the SSH key
        try:
            rsa_ssh_key = paramiko.RSAKey.from_private_key(
                io.StringIO(ssh_key),
                password=rsa_ssh_key_passphrase
            )
        except paramiko.ssh_exception.SSHException as e:
            logger.error("Failed to parse SSH key: %s", e)

        # Attempt logging in to the HyperAI instance
        try:
            paramiko_client = paramiko.client.SSHClient()
            paramiko_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            paramiko_client.connect(
                hostname=self.config.ip_address,
                username=self.config.username,
                pkey=rsa_ssh_key,
                timeout=30
            )
            paramiko_client.close()
        except paramiko.ssh_exception.BadHostKeyException as e:
            logger.error("Bad host key: %s", e)
        except paramiko.ssh_exception.AuthenticationException as e:
            logger.error("Authentication failed: %s", e)
        except paramiko.ssh_exception.SSHException as e:
            logger.error("SSH error: %s", e)
        except Exception as e:
            logger.error("Unknown error: %s", e)
    

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
        """
        Configure a local client to authenticate and connect to a resource.
        There is no local client for the HyperAI connector, so it does nothing.
        """
        pass

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "HyperAIServiceConnector":
        """Auto-configure the connector.

        Not supported by the HyperAI connector.

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
            "Auto-configuration is not supported by the HyperAI connector."
        )


    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify that a connection can be established to the HyperAI instance.

        Args:
            resource_type: The type of resource to verify. Must be set to the
                Docker resource type.
            resource_id: The HyperAI instance to verify.

        Returns:
            The resource ID if the connection can be established.
        """
        self._authorize_client()
        return [resource_id] if resource_id else []
