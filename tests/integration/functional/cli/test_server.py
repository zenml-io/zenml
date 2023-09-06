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
from contextlib import ExitStack as does_not_raise

import pytest
import requests
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.cli.server import LOCAL_ZENML_SERVER_NAME
from zenml.config.global_config import GlobalConfiguration
from zenml.utils.networking_utils import scan_for_available_port
from zenml.zen_server.deploy import ServerDeployer

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

    down_command = cli.commands["down"]
    cli_runner.invoke(down_command)

    # sleep for a bit to let the server stop
    time.sleep(5)

    deployer = ServerDeployer()

    assert deployer.list_servers() == []


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenServer not supported as daemon on Windows.",
)
def test_server_cli_up_and_connect(clean_client, mocker):
    """Test spinning up and connecting to ZenServer."""
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
    cli_runner.invoke(up_command, ["--port", port, "--connect"])

    # sleep for a bit to let the server start
    time.sleep(5)

    deployer = ServerDeployer()
    server = deployer.get_server(LOCAL_ZENML_SERVER_NAME)

    gc = GlobalConfiguration()
    assert gc.store.url == server.status.url

    down_command = cli.commands["down"]
    cli_runner.invoke(down_command)


user_create_command = cli.commands["user"].commands["create"]
role_create_command = cli.commands["role"].commands["create"]


@pytest.mark.skip(
    reason="Test needs to delete the user and generally fixing to work"
)
def test_server_doesnt_raise_error_for_permissionless_user() -> None:
    """Test that the server doesn't raise an error for a permissionless user."""
    runner = CliRunner()

    new_role_name = "permissionless_role_for_axl"
    new_user_name = "aria_and_blupus"
    new_password = "kamicat"

    # create a role without any permissions
    runner.invoke(role_create_command, [new_role_name])

    # create a user with the permissionless role
    runner.invoke(
        user_create_command,
        [
            new_user_name,
            f"--password={new_password}",
            f"--role={new_role_name}",
        ],
    )

    # disconnect from the server
    runner.invoke(cli.commands["disconnect"])

    server_url = GlobalConfiguration().store.url
    # try to connect to the server with the permissionless user
    with does_not_raise():
        result = runner.invoke(
            cli.commands["connect"],
            [
                f"--url={server_url}",
                f"--user={new_user_name}",
                f"--password={new_password}",
            ],
        )
        assert result.exit_code == 0
