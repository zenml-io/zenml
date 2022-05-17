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
import os
import shutil
import textwrap
from importlib import import_module
from json import JSONDecodeError
from typing import Optional, Union

import click
from click_params import IP_ADDRESS  # type: ignore[import]
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger

logger = get_logger(__name__)
GLOBAL_ZENML_SERVER_CONFIG_PATH = os.path.join(
    get_global_config_directory(),
    "zen_server",
)
ZENML_SERVER_CONFIG_FILENAME = os.path.join(
    GLOBAL_ZENML_SERVER_CONFIG_PATH, "service.json"
)


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
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


@server.command("up", help="Start a daemon service running the ZenServer.")
@click.option(
    "--ip-address", type=IP_ADDRESS, default="127.0.0.1", show_default=True
)
@click.option("--port", type=int, default=8000, show_default=True)
@click.option("--profile", type=str, default=None)
def up_server(
    ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
    port: int,
    profile: Optional[str],
) -> None:
    """Provisions resources for the ZenServer."""
    from zenml.services import ServiceRegistry
    from zenml.zen_server.zen_server import ZenServer, ZenServerConfig

    service_config = ZenServerConfig(
        root_runtime_path=GLOBAL_ZENML_SERVER_CONFIG_PATH,
        singleton=True,
        ip_address=str(ip_address),
        port=port,
    )
    if profile is not None:
        if GlobalConfiguration().get_profile(profile) is None:
            raise ValueError(f"Could not find profile of name {profile}.")
        service_config.profile_name = profile

    try:
        with open(ZENML_SERVER_CONFIG_FILENAME, "r") as f:
            zen_server = ServiceRegistry().load_service_from_json(f.read())
            cli_utils.declare(
                "An existing ZenServer local instance was found. To start a "
                "fresh instance, shut down the current one by running `zenml "
                "server down`. Reusing the existing ZenServer instance...",
            )
    except (JSONDecodeError, FileNotFoundError, ModuleNotFoundError, TypeError):
        zen_server = ZenServer(service_config)
        cli_utils.declare("Starting a new ZenServer local instance.")

    zen_server.start(timeout=30)

    # won't happen for ZenServer, but mypy complains otherwise
    assert zen_server.endpoint is not None

    if zen_server.endpoint.status.port != port:
        cli_utils.warning(
            textwrap.dedent(
                f"""
                You specified port={port}, but the current ZenServer is running
                at '{zen_server.endpoint.status.uri}'. This can happen in the
                case the specified port is in use or if the server was already
                running on port {zen_server.endpoint.status.port}.
                In case you want to change to port {port}, shut down the server
                with `zenml server down` and restart it with a free port of your
                choice.
                """
            )
        )
    else:
        cli_utils.declare(
            f"ZenServer running at '{zen_server.endpoint.status.uri}'."
        )


@server.command("status")
def status_server() -> None:
    """Get the status of the ZenServer."""
    from zenml.services import ServiceRegistry, ServiceState

    try:
        with open(ZENML_SERVER_CONFIG_FILENAME, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.warning("No ZenServer instance found locally!")
    else:
        zen_server_status = zervice.check_status()

        running = (
            f" and running at {zervice.endpoint.status.uri}."
            if zen_server_status[0] == ServiceState.ACTIVE and zervice.endpoint
            else ""
        )

        cli_utils.declare(
            f"The ZenServer status is {zen_server_status[0]}{running}."
        )


@server.command("down")
def down_server() -> None:
    """Shut down the local ZenServer instance."""
    from zenml.services import ServiceRegistry

    try:
        with open(ZENML_SERVER_CONFIG_FILENAME, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.error("No ZenServer instance found locally!")
    else:
        cli_utils.declare("Shutting down the local ZenService instance.")
        zervice.stop()

        shutil.rmtree(GLOBAL_ZENML_SERVER_CONFIG_PATH)
