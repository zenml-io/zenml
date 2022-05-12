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
import os
import textwrap
from importlib import import_module
from json import JSONDecodeError
from typing import Optional

import click
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger

logger = get_logger(__name__)
SERVER_CONFIG_FILENAME = "ZenServer.json"
GLOBAL_ZENML_SERVER_CONFIG_FILEPATH = os.path.join(
    get_global_config_directory(), SERVER_CONFIG_FILENAME
)


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
)
def server() -> None:
    """ZenML server."""


@server.command("explain", help="Explain the the concept of the Zen Server.")
def explain_server() -> None:
    """Explain the concept of the Zen Server."""
    component_module = import_module("zenml.zen_server")

    if component_module.__doc__ is not None:
        md = Markdown(component_module.__doc__)
        console.print(md)


@server.command("up", help="Start a daemon service running the Zenml Server.")
@click.option("--port", type=int, default=8000, show_default=True)
@click.option("--profile", type=str, default=None)
def up_server(port: int, profile: Optional[str]) -> None:
    """Provisions resources for the zen server."""
    from zenml.services import ServiceRegistry
    from zenml.zen_server.zen_server import ZenServer, ZenServerConfig

    if profile is not None:
        profile_configuration = GlobalConfiguration().get_profile(profile)
        if profile_configuration is None:
            raise ValueError(f"Could not find profile of name {profile}.")
        service_config = ZenServerConfig(
            port=port, store_profile_configuration=profile_configuration
        )
    else:
        service_config = ZenServerConfig(port=port)

    try:
        with open(GLOBAL_ZENML_SERVER_CONFIG_FILEPATH, "r") as f:
            zen_server = ServiceRegistry().load_service_from_json(f.read())
    except (JSONDecodeError, FileNotFoundError, ModuleNotFoundError, TypeError):
        zen_server = ZenServer(service_config)

    cli_utils.declare(
        f"Provisioning resources for service "
        f"'{zen_server.SERVICE_TYPE.name}'."
    )

    zen_server.start(timeout=30)

    if zen_server.endpoint:
        if zen_server.endpoint.status.port != port:
            cli_utils.warning(
                textwrap.dedent(
                    f"""
                    You specified port={port} but the server is running at
                    '{zen_server.endpoint.status.uri}'. This can happen in the
                    case the specified port is in use or if the server was
                    already running on port {zen_server.endpoint.status.port}.
                    In case you want to change to port={port} shut down the
                    server with `zenml server down -y` and restart it with
                    a free port of your choice.
                    """
                )
            )
        else:
            cli_utils.declare(
                f"Zen Server running at '{zen_server.endpoint.status.uri}'."
            )
    else:
        raise ValueError("No endpoint found for Zen Server.")

    with open(GLOBAL_ZENML_SERVER_CONFIG_FILEPATH, "w") as f:
        f.write(zen_server.json(indent=4))


@server.command("status")
def status_server() -> None:
    """Get the status of the Zen Server."""
    from zenml.services import ServiceRegistry, ServiceState

    try:
        with open(GLOBAL_ZENML_SERVER_CONFIG_FILEPATH, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.warning("No service found!")
    else:
        zen_server_status = zervice.check_status()

        running = (
            f" and running at {zervice.endpoint.status.uri}."
            if zen_server_status[0] == ServiceState.ACTIVE and zervice.endpoint
            else ""
        )

        cli_utils.declare(
            f"The Zen Server status is {zen_server_status[0]}{running}."
        )


@server.command("down")
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Deprovisions local resources instead of suspending "
    "them. Use `-y/--yes` instead.",
)
def down_server(force: bool = False, old_force: bool = False) -> None:
    """Suspends resources of the local Zen Server."""
    from zenml.services import ServiceRegistry

    if old_force:
        force = old_force
        cli_utils.warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or "
            "`-y` instead."
        )

    try:
        with open(GLOBAL_ZENML_SERVER_CONFIG_FILEPATH, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.error("No running server found!")
    else:
        if force:
            cli_utils.declare(
                f"Deprovisioning resources for service "
                f"'{zervice.SERVICE_TYPE.name}'."
            )
            zervice.stop()

            os.remove(GLOBAL_ZENML_SERVER_CONFIG_FILEPATH)
        else:
            cli_utils.declare(
                f"Suspending resources for service"
                f" '{zervice.SERVICE_TYPE.name}'."
            )
            zervice.stop()
