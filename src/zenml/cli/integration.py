#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import List, Dict
import subprocess
import sys

import click
from zenml.cli.cli import cli
from zenml.cli.utils import (
    declare,
    error
)
from zenml.integrations.registry import integration_registry

from zenml.logger import get_logger

logger = get_logger(__name__)


# To be replaced by zenml impl of Subprocess
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


class IntegrationsHandler:

    def __init__(self) -> None:
        self.integrations = integration_registry.integrations
        pass

    @property
    def list_integration_names(self) -> List[str]:
        return [name for name in self.integrations]

    def select_integration_requirements(self, integration_name: str = None):
        if integration_name:
            if integration_name in self.list_integration_names:
                return self.integrations[integration_name].REQUIREMENTS
            else:
                # If the github action executes this,
                # it might make sense to raise an error as well as logging
                error(
                    f"Version {integration_name} does not exist. "
                    f"Currently the following integrations are implemented. \n"
                    f"{self.list_integration_names}"
                )
                return
        else:
            return [
                requirement
                for name in self.list_integration_names
                for requirement in self.integrations[name].REQUIREMENTS
            ]


pass_integrations_handler = click.make_pass_decorator(
    IntegrationsHandler, ensure=True
)


@cli.group(help="Interact with the requirements of external integrations")
def integration() -> None:
    """Integrations group"""


@integration.command(help="List the available integration .")
def list() -> None:
    """List all available integrations."""
    declare("Listing integrations: \n")

    for name, integration_impl in integration_registry.integrations.items():
        is_installed = integration_impl.check_installation()
        # Formatting could be improved to be uniform and straightforward
        declare(f"{name} - {integration_impl.REQUIREMENTS}"
                f"{' - installed' if is_installed else ''}")

    declare("\nTo install the dependencies of a specific integration, type: ")
    declare("zenml integration install EXAMPLE_NAME")


@integration.command(help="List the available integration .")
@pass_integrations_handler
@click.argument("integration_name", required=False, default=None)
def get_requirements(integrations_handler: IntegrationsHandler,
                     integration_name: str) -> None:
    """List all requirements for the chosen integration."""
    requirements = integrations_handler.select_integration_requirements(
        integration_name
    )

    if requirements:
        declare("Listing requirements for {integration_name}: \n")
        declare(f"{requirements}")
        declare("\nTo install the dependencies of a "
                "specific integration, type: ")
        declare("zenml integration install EXAMPLE_NAME")


@integration.command(help="Install the required packages "
                          "for your integration of choice.")
@pass_integrations_handler
@click.argument("integration_name", required=False, default=None)
def install(integrations_handler: IntegrationsHandler, integration_name: str):
    requirements = integrations_handler.select_integration_requirements(
        integration_name
    )

    if requirements:
        ## should this rerun if already installed?
        declare(f"Installing all required packages for {integration_name}")
        for requirement in requirements:
            install_package(requirement)


if __name__ == '__main__':
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(integration, ['get-requirements'])
