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

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli

# Stacks
from zenml.zervice.zen_service_deployment import (
    ZenServiceDeploymentService,
    ZenServiceDeploymentConfig
)


@cli.group()
def service() -> None:
    """ZenMl server."""


@service.command("up")
def up_server() -> None:
    """Provisions resources for the stack."""
    service = ZenServiceDeploymentService(
        ZenServiceDeploymentConfig(port=5555)
    )
    cli_utils.declare(f"Provisioning resources for stack "
                      f"'{service.SERVICE_TYPE.name}'.")
    service.start()


@service.command("down")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_service(force: bool = False) -> None:
    """Suspends resources of the local stack deployment."""
    service = ZenServiceDeploymentService()

    if force:
        cli_utils.declare(
            f"Deprovisioning resources for stack '{service.SERVICE_TYPE.name}'."
        )
        service.stop()
    else:
        cli_utils.declare(f"Suspending resources for stack"
                          f" '{service.SERVICE_TYPE.name}'.")
        service.stop()
