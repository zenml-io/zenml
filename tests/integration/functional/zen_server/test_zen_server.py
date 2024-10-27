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
import os
import platform

import pytest
import requests

from zenml.client import Client
from zenml.constants import DEFAULT_USERNAME
from zenml.enums import StoreType
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_server.deploy import (
    LocalServerDeployer,
    LocalServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError
from zenml.zen_server.utils import server_config
from zenml.zen_stores.rest_zen_store import RestZenStore

SERVER_START_STOP_TIMEOUT = 60


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_server_up_down(clean_client, mocker):
    """Test spinning up and shutting down ZenServer."""
    # on MAC OS, we need to set this environment variable
    # to fix problems with the fork() calls (see this thread
    # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
    mocker.patch.dict(
        os.environ, {"OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES"}
    )
    port = scan_for_available_port(start=8003, stop=9000)
    deployment_config = LocalServerDeploymentConfig(
        provider="daemon",
        port=port,
    )
    endpoint = f"http://127.0.0.1:{port}"
    deployer = LocalServerDeployer()

    try:
        server = deployer.deploy_server(
            deployment_config, timeout=SERVER_START_STOP_TIMEOUT
        )
        assert server.status is not None
        assert server.status.url == endpoint
        assert (
            requests.head(endpoint + "/health", timeout=31).status_code == 200
        )
    except RuntimeError:
        print("ZenServer failed to start. Pulling logs...")
        for line in deployer.get_server_logs(tail=200):
            print(line)
        raise
    finally:
        try:
            deployer.remove_server(timeout=SERVER_START_STOP_TIMEOUT)
        except RuntimeError:
            print("ZenServer failed to start. Pulling logs...")
            for line in deployer.get_server_logs(tail=200):
                print(line)
            raise
    with pytest.raises(ServerDeploymentNotFoundError):
        assert deployer.get_server()


def test_rate_limit_is_not_impacted_by_successful_requests():
    zen_store = Client().zen_store
    if zen_store.type == StoreType.SQL:
        pytest.skip("SQL ZenStore does not support rate limiting.")

    assert Client().active_user.name == DEFAULT_USERNAME
    zen_store: RestZenStore = zen_store

    repeat = server_config().login_rate_limit_minute * 2
    for _ in range(repeat):
        zen_store.authenticate()
        zen_store.session
