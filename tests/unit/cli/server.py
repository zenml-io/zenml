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

import click
import pytest
import requests

from zenml.cli.server import up, down
from zenml.config.global_config import GlobalConfiguration
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_server.deploy import ServerDeployer, ServerDeploymentConfig

SERVER_START_STOP_TIMEOUT = 30


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
@click.pass_context
def test_server_up_down(clean_client, cli_runnner):
    """Test spinning up and shutting down ZenServer."""
    port = scan_for_available_port(start=8003, stop=9000)
    cli_runnner.invoke(up, ["--port", port])

    endpoint = f"http://127.0.0.1:{port}"
    assert requests.head(endpoint + "/health").status_code == 200

    cli_runnner.invoke(down)
    deployer = ServerDeployer()

    assert deployer.list_servers() == []


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
@click.pass_context
def test_server_up_and_connect(clean_client, cli_runner):
    """Test spinning up and connecting to ZenServer."""
    port = scan_for_available_port(start=8003, stop=9000)
    cli_runner.invoke(up, ["--port", port, "--connect", True])

    endpoint = f"http://127.0.0.1:{port}"

    gc = GlobalConfiguration()
    assert gc.store.url == endpoint
