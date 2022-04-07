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
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.services import ServiceRegistry, ServiceState
from zenml.zen_service.zen_service import ZenService, ZenServiceConfig

logger = get_logger(__name__)
SERVICE_CONFIG_FILENAME = "ZenService.json"
GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH = os.path.join(
    get_global_config_directory(), SERVICE_CONFIG_FILENAME
)


@cli.group()
def service() -> None:
    """ZenMl server."""


@service.command("explain", help="Explain the service")
def explain_service() -> None:
    """Explain the concept of the Zen Service."""
    component_module = import_module("zenml.zen_service")

    if component_module.__doc__ is not None:
        md = Markdown(component_module.__doc__)
        console.print(md)


@service.command("up", help="Start a daemon service running the zenml service")
@click.option("--port", type=int, default=8000, show_default=True)
@click.option("--profile", type=str, default=None)
def up_server(port: int, profile: Optional[str]) -> None:
    """Provisions resources for the zen service."""
    if profile is not None:
        profile_configuration = GlobalConfiguration().get_profile(profile)
        if profile_configuration is None:
            raise ValueError(f"Could not find profile of name {profile}.")
        service_config = ZenServiceConfig(
            port=port, store_profile_configuration=profile_configuration
        )
    else:
        service_config = ZenServiceConfig(port=port)

    try:
        with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "r") as f:
            zen_service = ServiceRegistry().load_service_from_json(f.read())
    except (JSONDecodeError, FileNotFoundError, ModuleNotFoundError):
        zen_service = ZenService(service_config)

    cli_utils.declare(
        f"Provisioning resources for service "
        f"'{zen_service.SERVICE_TYPE.name}'."
    )

    zen_service.start(timeout=30)

    if zen_service.endpoint:
        if zen_service.endpoint.status.port != port:
            cli_utils.warning(
                textwrap.dedent(
                    f"""
                    You specified port={port} but the service is running at
                    '{zen_service.endpoint.status.uri}'. This can happen in the
                    case the specified port is in use or if the service was
                    already running on port {zen_service.endpoint.status.port}.
                    In case you want to change to port={port} shut down the
                    service with `zenml service down -f` and restart it with
                    a free port of your choice.
                    """
                )
            )
        else:
            cli_utils.declare(
                f"Zenml Service running at '{zen_service.endpoint.status.uri}'."
            )
    else:
        raise ValueError("No endpoint found for Zen Service.")
    with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "w") as f:
        f.write(zen_service.json(indent=4))


@service.command("status")
def status_server() -> None:
    """Get the status of the zen service."""
    try:
        with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.warning("No service found!")
    else:
        zen_service_status = zervice.check_status()

        running = (
            f" and running at {zervice.endpoint.status.uri}."
            if zen_service_status[0] == ServiceState.ACTIVE and zervice.endpoint
            else ""
        )

        cli_utils.declare(
            f"The Zenml Service status is {zen_service_status[0]}{running}."
        )


@service.command("down")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_service(force: bool = False) -> None:
    """Suspends resources of the local zen service."""

    try:
        with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.error("No running service found!")
    else:
        if force:
            cli_utils.declare(
                f"Deprovisioning resources for service "
                f"'{zervice.SERVICE_TYPE.name}'."
            )
            zervice.stop()

            os.remove(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH)
        else:
            cli_utils.declare(
                f"Suspending resources for service"
                f" '{zervice.SERVICE_TYPE.name}'."
            )
            zervice.stop()
