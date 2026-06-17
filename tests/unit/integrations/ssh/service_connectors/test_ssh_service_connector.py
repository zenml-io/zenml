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
"""Unit tests for the SSH service connector."""

from unittest.mock import MagicMock, patch

import pytest

from zenml.exceptions import AuthorizationException
from zenml.integrations.ssh import SSH_CONNECTOR_TYPE, SSH_HOST_RESOURCE_TYPE
from zenml.integrations.ssh.service_connectors.ssh_service_connector import (
    SSHAuthenticationMethods,
    SSHHostConfiguration,
    SSHServiceConnector,
)
from zenml.integrations.ssh.ssh_utils import SSHConnectionConfig
from zenml.utils.secret_utils import PlainSerializedSecretStr

_MODULE = "zenml.integrations.ssh.service_connectors.ssh_service_connector"


def _make_connector(resource_id: str = "gpu-box") -> SSHServiceConnector:
    """Build an SSH service connector for tests."""
    return SSHServiceConnector(
        auth_method=SSHAuthenticationMethods.PRIVATE_KEY,
        resource_type=SSH_HOST_RESOURCE_TYPE,
        resource_id=resource_id,
        config=SSHHostConfiguration(
            hostnames=["gpu-box", "backup-box"],
            username="ubuntu",
            port=2222,
            ssh_private_key=PlainSerializedSecretStr("PRIVATE KEY"),
            ssh_key_passphrase=PlainSerializedSecretStr("passphrase"),
            verify_host_key=False,
            connection_timeout=15.0,
            keepalive_interval=10,
        ),
    )


def test_connector_type_metadata() -> None:
    connector_type = SSHServiceConnector.get_type()

    assert connector_type.connector_type == SSH_CONNECTOR_TYPE
    assert SSH_HOST_RESOURCE_TYPE in connector_type.resource_type_dict
    assert (
        SSHAuthenticationMethods.PRIVATE_KEY in connector_type.auth_method_dict
    )


def test_connect_returns_shared_connection_config() -> None:
    connection_config = _make_connector().connect(verify=False)

    assert isinstance(connection_config, SSHConnectionConfig)
    assert connection_config.hostname == "gpu-box"
    assert connection_config.port == 2222
    assert connection_config.username == "ubuntu"
    assert connection_config.ssh_private_key == "PRIVATE KEY"
    assert connection_config.ssh_key_passphrase == "passphrase"
    assert connection_config.verify_host_key is False
    assert connection_config.connection_timeout == 15.0
    assert connection_config.keepalive_interval == 10


def test_resource_id_is_normalized() -> None:
    connector = _make_connector(resource_id=" gpu-box ")

    assert connector.resource_id == "gpu-box"


def test_verify_rejects_unknown_hostname() -> None:
    connector = _make_connector()

    with pytest.raises(AuthorizationException, match="not in the configured"):
        connector._verify(resource_id="unknown")


def test_verify_opens_ssh_connection_for_allowed_host() -> None:
    connector = _make_connector()

    with patch(f"{_MODULE}.SSHClient") as ssh_client:
        ssh_client.return_value.__enter__.return_value = MagicMock()
        connector._verify(resource_id="backup-box")

    connection_config = ssh_client.call_args.args[0]
    assert isinstance(connection_config, SSHConnectionConfig)
    assert connection_config.hostname == "backup-box"
