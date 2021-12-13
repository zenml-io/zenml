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

from typing import List, Optional

import click
from tabulate import tabulate

from zenml.cli.cli import cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    install_package,
    title,
    uninstall_package,
    warning,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

logger = get_logger(__name__)


class IntegrationsHandler:
    """Handling the different integrations from the integration
    registry"""

    def __init__(self) -> None:
        self.integrations = integration_registry.integrations

    @property
    def list_integration_names(self) -> List[str]:
        """Get a list of all possible integrations"""
        return [name for name in self.integrations]

    def select_integration_requirements(
        self, integration_name: Optional[str] = None
    ) -> List[str]:
        """Select the requirements for a given integration
        or all integrations"""
        if integration_name:
            if integration_name in self.list_integration_names:
                return self.integrations[integration_name].REQUIREMENTS
            else:
                raise KeyError(
                    f"Version {integration_name} does not exist. "
                    f"Currently the following integrations are implemented. "
                    f"{self.list_integration_names}"
                )
        else:
            return [
                requirement
                for name in self.list_integration_names
                for requirement in self.integrations[name].REQUIREMENTS
            ]

    def is_installed(self, integration_name: str) -> bool:
        """Checks if all requirements for an integration are installed"""
        if integration_name in self.list_integration_names:
            return self.integrations[integration_name].check_installation()
        elif not integration_name:
            all_installed = [
                self.integrations[item].check_installation()
                for item in self.list_integration_names
            ]
            return all(all_installed)
        else:
            raise KeyError(
                f"Version {integration_name} does not exist. "
                f"Currently the following integrations are available. "
                f"{self.list_integration_names}"
            )


pass_integrations_handler = click.make_pass_decorator(
    IntegrationsHandler, ensure=True
)


@cli.group(help="Interact with the requirements of external integrations")
def integration() -> None:
    """Integrations group"""


@integration.command(help="List the available integration .")
def list() -> None:
    """List all available integrations with their installation status."""
    title("Integrations:\n")

    table_rows = []
    for name, integration_impl in integration_registry.integrations.items():
        is_installed = integration_impl.check_installation()
        table_rows.append(
            {
                "Integration": name,
                "Required Packages": integration_impl.REQUIREMENTS,
                "Installed": is_installed,
            }
        )
    declare(tabulate(table_rows, headers="keys"))

    warning("\nTo install the dependencies of a specific integration, type: ")
    warning("zenml integration install EXAMPLE_NAME")


@integration.command(help="List the available integration .")
@pass_integrations_handler
@click.argument("integration_name", required=False, default=None)
def get_requirements(
    integrations_handler: IntegrationsHandler, integration_name: str
) -> None:
    """List all requirements for the chosen integration."""
    try:
        requirements = integrations_handler.select_integration_requirements(
            integration_name
        )
    except KeyError as e:
        error(str(e))

    if requirements:
        title(
            f"Requirements for "
            f"{integration_name if integration_name else 'all integrations'}"
            f":\n"
        )
        declare(f"{requirements}")
        warning(
            "\nTo install the dependencies of a " "specific integration, type: "
        )
        warning("zenml integration install EXAMPLE_NAME")


@integration.command(
    help="Install the required packages " "for the integration of choice."
)
@pass_integrations_handler
@click.argument("integration_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the installation of the required packages. This will skip the "
    "confirmation step and reinstall existing packages as well",
)
def install(
    integrations_handler: IntegrationsHandler,
    integration_name: str,
    force: bool = False,
) -> None:
    """Installs the required packages for a given integration. If no integration
    is specified all required packages for all integrations are installed
    using pip"""
    try:
        if not integrations_handler.is_installed(integration_name) or force:
            requirements = integrations_handler.select_integration_requirements(
                integration_name
            )
        else:
            warning(
                "All required packages are already installed. "
                "Nothing will be done."
            )
            requirements = []
    except KeyError as e:
        error(str(e))

    if requirements:
        if force:
            declare(f"Installing all required packages for {integration_name}")
            for requirement in requirements:
                install_package(requirement)
        else:
            if confirmation(
                "Are you sure you want to install the following "
                "packages to the current environment?\n"
                f"{requirements}"
            ):
                for requirement in requirements:
                    install_package(requirement)


@integration.command(
    help="Uninstall the required packages " "for the integration of choice."
)
@pass_integrations_handler
@click.argument("integration_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the uninstallation of the required packages. This will skip "
    "the confirmation step",
)
def uninstall(
    integrations_handler: IntegrationsHandler,
    integration_name: str,
    force: bool = False,
) -> None:
    """Installs the required packages for a given integration. If no integration
    is specified all required packages for all integrations are installed
    using pip"""
    try:
        if integrations_handler.is_installed(integration_name):
            requirements = integrations_handler.select_integration_requirements(
                integration_name
            )
        else:
            warning(
                "The specified requirements already not installed."
                " Nothing will be done."
            )
            requirements = []
    except KeyError as e:
        error(str(e))

    if requirements:
        if force:
            declare(f"Installing all required packages for {integration_name}")
            for requirement in requirements:
                uninstall_package(requirement)
        else:
            if confirmation(
                "Are you sure you want to uninstall the following "
                "packages from the current environment?\n"
                f"{requirements}"
            ):
                for requirement in requirements:
                    uninstall_package(requirement)
