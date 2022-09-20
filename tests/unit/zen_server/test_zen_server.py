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
import platform

import pytest
import requests

from zenml.constants import (
    DEFAULT_LOCAL_SERVICE_IP_ADDRESS,
    STACK_CONFIGURATIONS,
    STACKS,
    USERS,
)
from zenml.services import (
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceState,
)
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_server.deploy.local.local_zen_server import (
    ZEN_SERVER_HEALTHCHECK_URL_PATH,
    LocalDaemonServiceEndpoint,
    LocalServerDeploymentConfig,
    LocalZenServer,
    LocalZenServerConfig,
)
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

SERVER_START_STOP_TIMEOUT = 15


@pytest.fixture
def running_zen_server(
    tmp_path_factory: pytest.TempPathFactory,
) -> LocalZenServer:
    """Spin up a ZenServer to do tests on."""
    port = scan_for_available_port(start=8003, stop=9000)
    zen_server = LocalZenServer(
        config=LocalZenServerConfig(
            server=LocalServerDeploymentConfig(name="", provider="local"),
        ),
        port=port,
        endpoint=LocalDaemonServiceEndpoint(
            config=LocalDaemonServiceEndpointConfig(
                protocol=ServiceEndpointProtocol.HTTP,
                ip_address=str(DEFAULT_LOCAL_SERVICE_IP_ADDRESS),
                port=port,
                allocate_port=False,
            ),
            monitor=HTTPEndpointHealthMonitor(
                config=HTTPEndpointHealthMonitorConfig(
                    healthcheck_uri_path=ZEN_SERVER_HEALTHCHECK_URL_PATH,
                    use_head_request=True,
                ),
            ),
        ),
    )

    zen_server.start(timeout=SERVER_START_STOP_TIMEOUT)

    yield zen_server
    zen_server.stop(timeout=SERVER_START_STOP_TIMEOUT)

    assert zen_server.check_status()[0] == ServiceState.INACTIVE


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_get_stack_endpoints(running_zen_server: LocalZenServer):
    """Test that the stack methods behave as they should."""
    endpoint = running_zen_server.endpoint.status.uri.strip("/")
    stacks_response = requests.get(
        endpoint + STACKS, auth=(DEFAULT_USERNAME, "")
    )
    assert stacks_response.status_code == 200
    assert isinstance(stacks_response.json(), (list, tuple))
    assert len(stacks_response.json()) == 1

    configs_response = requests.get(
        endpoint + STACK_CONFIGURATIONS, auth=(DEFAULT_USERNAME, "")
    )
    assert configs_response.status_code == 200
    assert isinstance(configs_response.json(), dict)
    assert len(configs_response.json()) == 1


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_server_requires_auth(running_zen_server: LocalZenServer):
    """Test that most service methods require authorization."""
    endpoint = running_zen_server.endpoint.status.uri.strip("/")
    stacks_response = requests.get(endpoint + STACKS)
    assert stacks_response.status_code == 401

    users_response = requests.get(endpoint + USERS)
    assert users_response.status_code == 401

    # health doesn't require auth
    health_response = requests.get(endpoint + "/health")
    assert health_response.status_code == 200


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_server_up_down():
    """Test spinning up and shutting down ZenServer."""
    port = scan_for_available_port(start=8003, stop=9000)
    zen_server = LocalZenServer(
        LocalZenServerConfig(
            port=port,
        )
    )
    endpoint = f"http://127.0.0.1:{port}/"
    try:
        zen_server.start(timeout=SERVER_START_STOP_TIMEOUT)
        assert zen_server.check_status()[0] == ServiceState.ACTIVE
        assert zen_server.endpoint.status.uri == endpoint
        assert requests.head(endpoint + "health").status_code == 200
    finally:
        zen_server.stop(timeout=SERVER_START_STOP_TIMEOUT)
    assert zen_server.check_status()[0] == ServiceState.INACTIVE
