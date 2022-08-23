#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""CLI for manipulating ZenML local and global config file."""

import ipaddress
from importlib import import_module
from typing import Union

import click
from click_params import IP_ADDRESS  # type: ignore[import]
from rich.markdown import Markdown

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger

logger = get_logger(__name__)

help_message = "Commands for managing the ZenServer."

try:
    # Make sure all ZenServer dependencies are installed
    import fastapi  # noqa

    from zenml.zen_server.deploy.local.local_zen_server import (
        LocalZenServer,
        LocalZenServerConfig,
    )  # noqa

    server_installed = True
except ImportError:
    # Unable to import the ZenServer dependencies. Include a help message in
    # the `zenml server` CLI group and don't add any subcommands that would
    # just fail.
    server_installed = False
    help_message += (
        "\n\n**Note**: The ZenServer seems to be unavailable on your machine. "
        "This is probably because ZenML was installed without the optional "
        "ZenServer dependencies. To install the missing dependencies "
        f"run `pip install zenml=={zenml.__version__}[server]`."
    )


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
    help=help_message,
)
def server() -> None:
    """Commands for managing the ZenServer."""


if server_installed:

    @server.command("explain", help="Explain the ZenServer concept.")
    def explain_server() -> None:
        """Explain the ZenServer concept."""
        component_module = import_module("zenml.zen_server")

        if component_module.__doc__ is not None:
            md = Markdown(component_module.__doc__)
            console.print(md)

    @server.command("up", help="Start a daemon service running the ZenServer.")
    @click.option(
        "--ip-address", type=IP_ADDRESS, default="127.0.0.1", show_default=True
    )
    @click.option("--port", type=int, default=8237, show_default=True)
    @click.option("--username", type=str, default="default", show_default=True)
    @click.option("--password", type=str, default="", show_default=True)
    def up_server(
        ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
        port: int,
        username: str,
        password: str,
    ) -> None:
        """Provisions resources for the ZenServer.

        Args:
            ip_address: The IP address to bind the server to.
            port: The port to bind the server to.
            username: The username to use for authentication.
            password: The password to use for authentication.
        """
        from zenml.zen_server.deploy.local.local_deployer import (
            LocalServerDeployer,
            LocalServerDeploymentConfig,
            LOCAL_SERVER_SINGLETON_NAME,
        )

        server_config = LocalServerDeploymentConfig(
            name=LOCAL_SERVER_SINGLETON_NAME,
            address=ip_address,
            port=port,
            username=username,
            password=password,
        )

        deployer = LocalServerDeployer()
        deployer.up(server_config)

        server_status = deployer.status(LOCAL_SERVER_SINGLETON_NAME)
        cli_utils.declare(
            f"Local ZenML server running at '{server_status.url}'."
        )

    @server.command("status")
    def status_server() -> None:
        """Get the status of the ZenServer."""
        from zenml.zen_server.deploy.local.local_deployer import (
            LocalServerDeployer,
            LOCAL_SERVER_SINGLETON_NAME,
        )

        deployer = LocalServerDeployer()
        try:
            server_status = deployer.status(LOCAL_SERVER_SINGLETON_NAME)
        except KeyError:
            cli_utils.error("No ZenML server running locally!")

        cli_utils.declare(
            f"Local ZenML server running at '{server_status.url}'."
        )

    @server.command("down")
    def down_server() -> None:
        """Shut down the local ZenServer instance."""
        from zenml.zen_server.deploy.local.local_deployer import (
            LocalServerDeployer,
            LOCAL_SERVER_SINGLETON_NAME,
        )

        deployer = LocalServerDeployer()
        try:
            deployer.get(LOCAL_SERVER_SINGLETON_NAME)
        except KeyError:
            cli_utils.error("No ZenML server running locally!")

        deployer.down(LOCAL_SERVER_SINGLETON_NAME)

    @server.command("connect")
    @click.argument(
        "server",
        type=str,
        required=True,
    )
    @click.option("--user", type=str, default="default", show_default=True)
    def connect_server(server: str, user: str) -> None:
        """Connect to a ZenServer."""
        from zenml.zen_server.deploy.local.local_deployer import (
            LocalServerDeployer,
        )

        deployer = LocalServerDeployer()
        try:
            deployer.connect(server=server, user=user)
        except KeyError:
            cli_utils.error("No ZenML server running locally!")

        cli_utils.declare(f"Connected to the {server} server as user {user}.")

    @server.command("disconnect")
    @click.argument(
        "server",
        type=str,
        required=True,
    )
    def disconnect_server(server: str) -> None:
        """Disconnect from a ZenServer."""
        from zenml.zen_server.deploy.local.local_deployer import (
            LocalServerDeployer,
        )

        deployer = LocalServerDeployer()
        try:
            deployer.disconnect(server=server)
        except KeyError:
            cli_utils.error("No ZenML server running locally!")

        cli_utils.declare(f"Disconnected from the {server} server.")
