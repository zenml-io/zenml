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
import os
import platform
import time

import pytest
import requests
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.cli.server import LOCAL_ZENML_SERVER_NAME
from zenml.config.global_config import GlobalConfiguration
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_server.deploy import LocalServerDeployer

SERVER_START_STOP_TIMEOUT = 30


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_server_cli_up_down(clean_client, mocker):
    """Test spinning up and shutting down ZenServer."""
    mocker.patch.dict(
        os.environ, {"OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES"}
    )
    mocker.patch(
        "zenml.zen_server.deploy.local.local_provider.LOCAL_ZENML_SERVER_DEFAULT_TIMEOUT",
        60,
    )
    cli_runner = CliRunner()

    port = scan_for_available_port(start=8003, stop=9000)
    up_command = cli.commands["up"]
    cli_runner.invoke(up_command, ["--port", port])

    # sleep for a bit to let the server start
    time.sleep(5)

    endpoint = f"http://127.0.0.1:{port}"
    assert requests.head(endpoint + "/health", timeout=16).status_code == 200

    deployer = LocalServerDeployer()
    server = deployer.get_server(LOCAL_ZENML_SERVER_NAME)
    gc = GlobalConfiguration()
    assert gc.store.url == server.status.url

    # patch `gc.set_default_store()` to return None
    mocker.patch.object(
        GlobalConfiguration, "set_default_store", return_value=None
    )
    down_command = cli.commands["down"]
    cli_runner.invoke(down_command)

    # sleep for a bit to let the server stop
    time.sleep(5)

    deployer = LocalServerDeployer()
    assert deployer.list_servers() == []
