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
"""CLI for managing ZenML server deployments."""

import ipaddress
from importlib import import_module
from typing import Any, Dict, Optional, Union

import click
from click_params import IP_ADDRESS
from rich.errors import MarkupError
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.console import console
from zenml.enums import CliCategories, ServerProviderType
from zenml.logger import get_logger
from zenml.zen_server.deploy.deployer import ServerDeployer
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError

logger = get_logger(__name__)

help_message = "Commands for managing the ZenServer."


def get_one_server(server_name: Optional[str]) -> ServerDeployment:
    """Get a single server deployment by name.

    Call this function to retrieve a single server deployment. If no name is
    provided and there is only one server deployment, that one will be returned,
    otherwise an error will be raised.

    Args:
        server_name: Name of the server deployment.

    Returns:
        The server deployment.
    """
    deployer = ServerDeployer()
    servers = deployer.list_servers(server_name=server_name)

    if not servers:
        if server_name:
            cli_utils.error(
                f"No ZenML server with the name '{server_name}' was found !"
            )
        else:
            cli_utils.error("No ZenML servers were found !")
    elif len(servers) > 1:
        cli_utils.error(
            "Found multiple ZenML servers running. You have to supply a "
            "server name."
        )

    return servers[0]


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
@click.option("--name", type=str, help="Name for the ZenML server deployment.")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(
        [p.value for p in ServerProviderType], case_sensitive=True
    ),
    help="Server deployment provider.",
    default=ServerProviderType.LOCAL.value,
)
@click.option(
    "--connect",
    is_flag=True,
    help="Connect the client to the ZenML server after it's deployed.",
    type=click.BOOL,
)
@click.option("--port", type=int, default=None)
@click.option("--ip-address", type=IP_ADDRESS, default=None)
@click.option(
    "--username", type=str, default="default", show_default=True, help="The ."
)
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
    provider: str,
    connect: bool,
    username: str,
    password: str,
    name: Optional[str],
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    timeout: Optional[int] = None,
    port: Optional[int] = None,
) -> None:
    """Provisions resources for a ZenML server.

    Args:
        name: Name for the ZenML server deployment.
        provider: ZenML server provider name.
        connect: Connecting the client to the ZenML server.
        ip_address: The IP address to bind the server to.
        port: The port to bind the server to.
        username: The username to use for authentication.
        password: The password to use for authentication.
        timeout: Time in seconds to wait for the server to start.
    """
    name = name or provider
    config_attrs: Dict[str, Any] = dict(
        name=name,
        provider=ServerProviderType(provider),
    )
    if port is not None:
        config_attrs["port"] = port
    if ip_address is not None:
        config_attrs["ip_address"] = ip_address

    deployer = ServerDeployer()
    server_config = ServerDeploymentConfig(**config_attrs)

    server = deployer.deploy_server(server_config, timeout=timeout)
    if server.status and server.status.url:
        cli_utils.declare(
            f"ZenML server '{name}' running at '{server.status.url}'."
        )
    if connect:
        deployer.connect_to_server(name, username, password)


@server.command("down", help="Shut down and remove a ZenML server instance.")
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=None,
    help=(
        "Time in seconds to wait for the server to stop. Set to 0 to "
        "return immediately after stopping the server, without waiting for it "
        "to shut down."
    ),
)
@click.argument(
    "server_name",
    type=str,
    required=False,
)
def down_server(
    server_name: Optional[str], timeout: Optional[int] = None
) -> None:
    """Shut down a ZenML server instance.

    Args:
        server_name: Name of the ZenML server deployment.
        timeout: Time in seconds to wait for the server to stop.
    """
    server = get_one_server(server_name)
    server_name = server.config.name
    deployer = ServerDeployer()

    try:
        deployer.remove_server(server_name, timeout=timeout)
    except ServerDeploymentNotFoundError as e:
        cli_utils.error(f"Server not found: {e}")

    cli_utils.declare(f"Removed the '{server_name}' ZenML server.")


@server.command("status", help="Get the status of a ZenML server.")
@click.argument(
    "server_name",
    type=str,
    required=False,
)
def status_server(server_name: Optional[str] = None) -> None:
    """Get the status of a ZenML server.

    Args:
        server_name: Name of the ZenML server deployment.
    """
    server = get_one_server(server_name)
    server_name = server.config.name

    cli_utils.print_server_deployment(server)


@server.command("list", help="List the status of all ZenML servers.")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(
        [p.value for p in ServerProviderType], case_sensitive=True
    ),
    help="Server deployment provider.",
    default=None,
)
def list_servers(
    provider: Optional[str] = None,
) -> None:
    """List the status of all ZenML servers.

    Args:
        provider: Server deployment provider.
    """
    deployer = ServerDeployer()

    if provider is not None:
        servers = deployer.list_servers(
            provider_type=ServerProviderType(provider)
        )
    else:
        servers = deployer.list_servers()

    cli_utils.print_server_deployment_list(servers)


@server.command("connect", help="Connect to a ZenML server.")
@click.argument(
    "server_name",
    type=str,
    required=False,
)
@click.option("--username", type=str, default="default", show_default=True)
@click.option("--password", type=str, default="", show_default=True)
def connect_server(
    username: str,
    password: str,
    server_name: Optional[str] = None,
) -> None:
    """Connect to a ZenML server.

    Args:
        username: The username to use for authentication.
        password: The password to use for authentication.
        server_name: Name of the ZenML server deployment.
    """
    server = get_one_server(server_name)
    server_name = server.config.name
    deployer = ServerDeployer()

    try:
        deployer.connect_to_server(server_name, username, password)
    except ServerDeploymentNotFoundError as e:
        cli_utils.error(f"Server not found: {e}")


@server.command("disconnect", help="Disconnect from a ZenML server.")
@click.argument(
    "server_name",
    type=str,
    required=False,
)
def disconnect_server(server_name: Optional[str] = None) -> None:
    """Disconnect from a ZenML server.

    Args:
        server_name: Name of the ZenML server deployment.
    """
    deployer = ServerDeployer()

    try:
        deployer.disconnect_from_server(server_name)
    except ServerDeploymentNotFoundError as e:
        cli_utils.error(f"Server not found: {e}")


@server.command("logs", help="Show the logs for a ZenML server.")
@click.argument(
    "server_name",
    type=click.STRING,
    required=False,
)
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
    follow: bool,
    raw: bool,
    tail: Optional[int] = None,
    server_name: Optional[str] = None,
) -> None:
    """Display the logs for a ZenML server.

    Args:
        server_name: The name of the ZenML server instance.
        follow: Continue to output new log data as it becomes available.
        tail: Only show the last NUM lines of log output.
        raw: Show raw log contents (don't pretty-print logs).
    """
    server = get_one_server(server_name)
    server_name = server.config.name
    deployer = ServerDeployer()

    try:
        logs = deployer.get_server_logs(server_name, follow=follow, tail=tail)
    except ServerDeploymentNotFoundError as e:
        cli_utils.error(f"Server not found: {e}")

    for line in logs:
        # don't pretty-print log lines that are already pretty-printed
        if raw or line.startswith("\x1b["):
            console.print(line, markup=False)
        else:
            try:
                console.print(line)
            except MarkupError:
                console.print(line, markup=False)
