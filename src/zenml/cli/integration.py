#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    install_package,
    print_table,
    title,
    uninstall_package,
    warning,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

logger = get_logger(__name__)


@cli.group(help="Interact with the requirements of external integrations.")
def integration() -> None:
    """Integrations group"""


@integration.command(name="list", help="List the available integrations.")
def list_integrations() -> None:
    """List all available integrations with their installation status."""
    title("Integrations:\n")

    table_rows = []
    for name, integration_impl in integration_registry.integrations.items():
        is_installed = integration_impl.check_installation()
        # TODO [ENG-253]: Make the installed column right-aligned once we
        #  add rich or some other similar dependency
        table_rows.append(
            {
                "INSTALLED": "*" if is_installed else "",
                "INTEGRATION": name,
                "REQUIRED_PACKAGES": integration_impl.REQUIREMENTS,
            }
        )
    print_table(table_rows)

    warning(
        "\n" + "To install the dependencies of a specific integration, type: "
    )
    warning("zenml integration install EXAMPLE_NAME")


@integration.command(
    name="requirements", help="List all requirements for an integration."
)
@click.argument("integration_name", required=False, default=None)
def get_requirements(integration_name: Optional[str] = None) -> None:
    """List all requirements for the chosen integration."""
    try:
        requirements = integration_registry.select_integration_requirements(
            integration_name
        )
    except KeyError as e:
        error(str(e))
    else:
        if requirements:
            title(
                f"Requirements for "
                f"{integration_name if integration_name else 'all integrations'}"
                f":\n"
            )
            declare(f"{requirements}")
            warning(
                "\n" + "To install the dependencies of a "
                "specific integration, type: "
            )
            warning("zenml integration install EXAMPLE_NAME")


@integration.command(
    help="Install the required packages for the integration of choice."
)
@click.argument("integration_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the installation of the required packages. This will skip the "
    "confirmation step and reinstall existing packages as well",
)
def install(
    integration_name: Optional[str] = None, force: bool = False
) -> None:
    """Installs the required packages for a given integration. If no integration
    is specified all required packages for all integrations are installed
    using pip"""
    try:
        if not integration_registry.is_installed(integration_name) or force:
            requirements = integration_registry.select_integration_requirements(
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
    else:
        if requirements:
            if force:
                declare(
                    f"Installing all required packages for "
                    f"{integration_name if integration_name else 'all integrations'}"
                )
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
    help="Uninstall the required packages for the integration of choice."
)
@click.argument("integration_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the uninstallation of the required packages. This will skip "
    "the confirmation step",
)
def uninstall(
    integration_name: Optional[str] = None, force: bool = False
) -> None:
    """Installs the required packages for a given integration. If no integration
    is specified all required packages for all integrations are installed
    using pip"""
    try:
        if integration_registry.is_installed(integration_name):
            requirements = integration_registry.select_integration_requirements(
                integration_name
            )
        else:
            warning(
                "The specified requirements already not installed. "
                "Nothing will be done."
            )
            requirements = []
    except KeyError as e:
        error(str(e))
    else:
        if requirements:
            if force:
                declare(
                    f"Installing all required packages for "
                    f"{integration_name if integration_name else 'all integrations'}"
                )
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
