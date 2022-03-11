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
from json import JSONDecodeError

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli

from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.services import ServiceRegistry, ServiceState
from zenml.zen_service.zen_service_deployment import (
    ZenServiceService,
    ZenServiceConfig
)

logger = get_logger(__name__)
SERVICE_CONFIG_FILENAME = "ZenService.json"
GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH = os.path.join(
    get_global_config_directory(), SERVICE_CONFIG_FILENAME)


@cli.group()
def service() -> None:
    """ZenMl server."""


@service.command("up", help="Start a daemon service running the zenml service")
@click.option("--port", required=False, type=int, default=8000)
def up_server(port) -> None:
    """Provisions resources for the zen service."""

    try:
        with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "r") as f:
            zen_service = ServiceRegistry().load_service_from_json(f.read())
    except (JSONDecodeError, FileNotFoundError, ModuleNotFoundError):
        zen_service = ZenServiceService(
            ZenServiceConfig(port=port)
        )

    cli_utils.declare(f"Provisioning resources for service "
                      f"'{zen_service.SERVICE_TYPE.name}'.")

    zen_service.start(timeout=10)

    if zen_service.endpoint.status.port != port:
        cli_utils.error(f"You specified port={port} but the service is "
                        f"running at '{zen_service.endpoint.status.uri}' "
                        f"This can happen in case the specified port is "
                        f"in use or if the service was already running "
                        f"on port{zen_service.endpoint.status.port}' "
                        f"In case you want to change to port={port} "
                        f"shut down the service with "
                        f"`zenml service down -f` and restart it with "
                        f"a free port of your choice.")
    else:
        cli_utils.declare("Zenml Service running at "
                          f"'{zen_service.endpoint.status.uri}'.")

    with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "w") as f:
        f.write(zen_service.json(indent=4))


@service.command("status")
def status_server() -> None:
    """Provisions resources for the stack."""
    try:
        with open(GLOBAL_ZENML_SERVICE_CONFIG_FILEPATH, "r") as f:
            zervice = ServiceRegistry().load_service_from_json(f.read())
    except FileNotFoundError:
        cli_utils.error("No service found!")
    else:
        zen_service_status = zervice.check_status()

        response_message = f"The Zenml Service status is " \
                           f"{zen_service_status[0]}"
        if zen_service_status[0] == ServiceState.ACTIVE:
            response_message += f" and running at " \
                                f"{zervice.endpoint.status.uri}."
        else:
            response_message += '.'

        cli_utils.declare(response_message)


@service.command("down")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_service(force: bool = False) -> None:
    """Suspends resources of the local stack deployment."""

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
            cli_utils.declare(f"Suspending resources for service"
                              f" '{zervice.SERVICE_TYPE.name}'.")
            zervice.stop()
