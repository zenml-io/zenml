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
from typing import Optional, Union

import click
from click_params import IP_ADDRESS  # type: ignore[import]
from rich.errors import MarkupError
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.zen_server.deploy.base_deployer import (
    BaseServerDeployer,
    BaseServerDeploymentConfig,
)
from zenml.zen_server.deploy.docker.docker_deployer import (
    DOCKER_SERVER_SINGLETON_NAME,
    DockerServerDeployer,
)
from zenml.zen_server.deploy.docker.docker_zen_server import (
    DockerServerDeploymentConfig,
)
from zenml.zen_server.deploy.local.local_deployer import (
    LOCAL_SERVER_SINGLETON_NAME,
    LocalServerDeployer,
)
from zenml.zen_server.deploy.local.local_zen_server import (
    LocalServerDeploymentConfig,
)

logger = get_logger(__name__)

help_message = "Commands for managing the ZenServer."


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
    help=help_message,
)
def server() -> None:
    """Commands for managing the ZenServer."""


@server.command("explain", help="Explain the ZenServer concept.")
def explain_server() -> None:
    """Explain the ZenServer concept."""
    component_module = import_module("zenml.zen_server")

    if component_module.__doc__ is not None:
        md = Markdown(component_module.__doc__)
        console.print(md)


@server.command("up", help="Provision and start a ZenML server.")
@click.option("--port", type=int, default=8237, show_default=True)
@click.option(
    "--local",
    is_flag=True,
    help="Deploy the ZenML server as a local daemon process.",
    type=click.BOOL,
)
@click.option(
    "--container",
    is_flag=True,
    help="Deploy the ZenML server as a container.",
    type=click.BOOL,
)
@click.option(
    "--skip-connect",
    is_flag=True,
    help="Don't automatically connecting the client to the ZenML server.",
    type=click.BOOL,
)
@click.option(
    "--ip-address", type=IP_ADDRESS, default="127.0.0.1", show_default=True
)
@click.option("--port", type=int, default=8237, show_default=True)
@click.option("--username", type=str, default="default", show_default=True)
@click.option("--password", type=str, default="", show_default=True)
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=None,
    help=(
        "Time in seconds to wait for the server to start. Set to 0 to "
        "return immediately after starting the server, without waiting for it "
        "to be ready."
    ),
)
def up_server(
    local: bool,
    container: bool,
    skip_connect: bool,
    ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
    port: int,
    username: str,
    password: str,
    timeout: Optional[int] = None,
) -> None:
    """Provisions resources for a ZenML server.

    Args:
        local: Deploy the ZenML server as a local daemon process.
        container: Deploy the ZenML server as a container.
        ip_address: The IP address to bind the server to.
        port: The port to bind the server to.
        username: The username to use for authentication.
        password: The password to use for authentication.
    """
    if local and container:
        cli_utils.error(
            "The `--local` and `--container` options are mutually exclusive."
        )
    if not local and not container:
        # Default to using the local daemon process deployment method
        local = True

    deployer: BaseServerDeployer
    server_config: BaseServerDeploymentConfig

    if local:
        deployer = LocalServerDeployer()

        server_config = LocalServerDeploymentConfig(
            name=LOCAL_SERVER_SINGLETON_NAME,
            address=ip_address,
            port=port,
            username=username,
            password=password,
        )

    elif container:
        deployer = DockerServerDeployer()

        server_config = DockerServerDeploymentConfig(
            name=DOCKER_SERVER_SINGLETON_NAME,
            port=port,
            username=username,
            password=password,
        )

    deployer.up(server_config, connect=not skip_connect, timeout=timeout)

    server_status = deployer.status(server_config.name)
    cli_utils.declare(
        f"ZenML server '{server_config.name}' running at '{server_status.url}'."
    )


@server.command("status")
@click.argument(
    "server",
    type=str,
    required=True,
)
def status_server(server: str) -> None:
    """Get the status of a ZenML server."""

    deployer: BaseServerDeployer
    if server == LOCAL_SERVER_SINGLETON_NAME:
        deployer = LocalServerDeployer()
    elif server == DOCKER_SERVER_SINGLETON_NAME:
        deployer = DockerServerDeployer()
    else:
        cli_utils.error(f"Unknown server '{server}'.")

    try:
        server_status = deployer.status(server)
    except KeyError:
        cli_utils.error(f"No ZenML server with the name '{server}' was found !")

    cli_utils.declare(f"Local ZenML server running at '{server_status.url}'.")


@server.command("down")
@click.argument(
    "server",
    type=str,
    required=True,
)
def down_server(server: str) -> None:
    """Shut down a ZenML server instance."""

    deployer: BaseServerDeployer
    if server == LOCAL_SERVER_SINGLETON_NAME:
        deployer = LocalServerDeployer()
    elif server == DOCKER_SERVER_SINGLETON_NAME:
        deployer = DockerServerDeployer()
    else:
        cli_utils.error(f"Unknown server '{server}'.")

    try:
        deployer.get(server)
    except KeyError:
        cli_utils.error(f"No ZenML server with the name '{server}' was found !")

    deployer.down(server)
    cli_utils.declare(f"Stopped the '{server}' ZenML server.")


@server.command("connect")
@click.argument(
    "server",
    type=str,
    required=True,
)
@click.option("--username", type=str, default="default", show_default=True)
@click.option("--password", type=str, default="", show_default=True)
def connect_server(server: str, username: str, password: str) -> None:
    """Connect to a ZenServer."""

    deployer: BaseServerDeployer
    if server == LOCAL_SERVER_SINGLETON_NAME:
        deployer = LocalServerDeployer()
    elif server == DOCKER_SERVER_SINGLETON_NAME:
        deployer = DockerServerDeployer()
    else:
        cli_utils.error(f"Unknown server '{server}'.")

    try:
        deployer.connect(server=server, username=username, password=password)
    except KeyError:
        cli_utils.error(f"No ZenML server with the name '{server}' was found !")

    cli_utils.declare(
        f"Connected to the '{server}' ZenML server as user {username}."
    )


@server.command("disconnect")
@click.argument(
    "server",
    type=str,
    required=True,
)
def disconnect_server(server: str) -> None:
    """Disconnect from a ZenServer."""

    deployer: BaseServerDeployer
    if server == LOCAL_SERVER_SINGLETON_NAME:
        deployer = LocalServerDeployer()
    elif server == DOCKER_SERVER_SINGLETON_NAME:
        deployer = DockerServerDeployer()
    else:
        cli_utils.error(f"Unknown server '{server}'.")

    try:
        deployer.disconnect(server=server)
    except KeyError:
        cli_utils.error(f"No ZenML server with the name '{server}' was found !")

    cli_utils.declare(f"Disconnected from the '{server}' ZenML server.")


@server.command("logs", help="Show the logs for a ZenML server.")
@click.argument("server", type=click.STRING)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Continue to output new log data as it becomes available.",
)
@click.option(
    "--tail",
    "-t",
    type=click.INT,
    default=None,
    help="Only show the last NUM lines of log output.",
)
@click.option(
    "--raw",
    "-r",
    is_flag=True,
    help="Show raw log contents (don't pretty-print logs).",
)
def get_server_logs(
    server: str,
    follow: bool,
    tail: Optional[int],
    raw: bool,
) -> None:
    """Display the logs for a ZenML server.

    Args:
        server: The name of the ZenML server instance.
        follow: Continue to output new log data as it becomes available.
        tail: Only show the last NUM lines of log output.
        raw: Show raw log contents (don't pretty-print logs).
    """

    deployer: BaseServerDeployer
    if server == LOCAL_SERVER_SINGLETON_NAME:
        deployer = LocalServerDeployer()
    elif server == DOCKER_SERVER_SINGLETON_NAME:
        deployer = DockerServerDeployer()
    else:
        cli_utils.error(f"Unknown server '{server}'.")

    try:
        logs = deployer.get_logs(server, follow=follow, tail=tail)
    except KeyError:
        cli_utils.error(f"No ZenML server with the name '{server}' was found !")

    for line in logs:
        # don't pretty-print log lines that are already pretty-printed
        if raw or line.startswith("\x1b["):
            console.print(line, markup=False)
        else:
            try:
                console.print(line)
            except MarkupError:
                console.print(line, markup=False)
