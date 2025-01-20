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
"""Functionality to install or uninstall ZenML integrations via the CLI."""

import sys
from typing import Optional, Tuple

import click
from rich.progress import track

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    format_integration_list,
    install_packages,
    print_table,
    title,
    uninstall_package,
    warning,
)
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger

logger = get_logger(__name__)


@cli.group(
    cls=TagGroup,
    tag=CliCategories.INTEGRATIONS,
)
def integration() -> None:
    """Interact with external integrations."""


@integration.command(name="list", help="List the available integrations.")
def list_integrations() -> None:
    """List all available integrations with their installation status."""
    from zenml.integrations.registry import integration_registry

    formatted_table = format_integration_list(
        sorted(list(integration_registry.integrations.items()))
    )
    print_table(formatted_table)
    warning(
        "\n" + "To install the dependencies of a specific integration, type: "
    )
    warning("zenml integration install INTEGRATION_NAME")


@integration.command(
    name="requirements", help="List all requirements for an integration."
)
@click.argument("integration_name", required=False, default=None)
def get_requirements(integration_name: Optional[str] = None) -> None:
    """List all requirements for the chosen integration.

    Args:
        integration_name: The name of the integration to list the requirements
            for.
    """
    from zenml.integrations.registry import integration_registry

    try:
        requirements = integration_registry.select_integration_requirements(
            integration_name
        )
    except KeyError as e:
        error(str(e))
    else:
        if requirements:
            title(
                f"Requirements for {integration_name or 'all integrations'}:\n"
            )
            declare(f"{requirements}")
            warning(
                "\n" + "To install the dependencies of a "
                "specific integration, type: "
            )
            warning("zenml integration install INTEGRATION_NAME")


@integration.command(
    name="export-requirements", help="Export the integration requirements."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--ignore-integration",
    "-i",
    multiple=True,
    help="List of integrations to ignore explicitly.",
)
@click.option(
    "--output-file",
    "-o",
    "output_file",
    type=str,
    required=False,
    help="File to which to export the integration requirements. If not "
    "provided, the requirements will be printed to stdout instead.",
)
@click.option(
    "--overwrite",
    "-ov",
    "overwrite",
    type=bool,
    required=False,
    is_flag=True,
    help="Overwrite the output file if it already exists. This option is "
    "only valid if the output file is provided.",
)
@click.option(
    "--installed-only",
    "installed_only",
    is_flag=True,
    default=False,
    help="Only export requirements for integrations installed in your current "
    "environment. This can not be specified when also providing explicit "
    "integrations.",
)
def export_requirements(
    integrations: Tuple[str],
    ignore_integration: Tuple[str],
    output_file: Optional[str] = None,
    overwrite: bool = False,
    installed_only: bool = False,
) -> None:
    """Exports integration requirements so they can be installed using pip.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        ignore_integration: List of integrations to ignore explicitly.
        output_file: Optional path to the requirements output file.
        overwrite: Overwrite the output file if it already exists. This option
            is only valid if the output file is provided.
        installed_only: Only export requirements for integrations installed in
            your current environment. This can not be specified when also
            providing explicit integrations.
    """
    from zenml.integrations.registry import integration_registry

    if installed_only and integrations:
        error(
            "You can either provide specific integrations or export only "
            "requirements for integrations installed in your local "
            "environment, not both."
        )

    all_integrations = set(integration_registry.integrations.keys())

    if integrations:
        integrations_to_export = set(integrations)
    elif installed_only:
        integrations_to_export = set(
            integration_registry.get_installed_integrations()
        )
    else:
        integrations_to_export = all_integrations

    for i in ignore_integration:
        try:
            integrations_to_export.remove(i)
        except KeyError:
            if i not in all_integrations:
                error(
                    f"Integration {i} does not exist. Available integrations: "
                    f"{all_integrations}"
                )

    requirements = []
    for integration_name in integrations_to_export:
        try:
            requirements += (
                integration_registry.select_integration_requirements(
                    integration_name
                )
            )
        except KeyError:
            error(f"Unable to find integration '{integration_name}'.")

    if output_file:
        try:
            with open(output_file, "x") as f:
                f.write("\n".join(requirements))
        except FileExistsError:
            if overwrite or confirmation(
                "A file already exists at the specified path. "
                "Would you like to overwrite it?"
            ):
                with open(output_file, "w") as f:
                    f.write("\n".join(requirements))
        declare(f"Requirements exported to {output_file}.")
    else:
        click.echo(" ".join(requirements), nl=False)


@integration.command(
    help="Install the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--ignore-integration",
    "-i",
    multiple=True,
    help="Integrations to ignore explicitly (passed in separately).",
)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the installation of the required packages. This will skip the "
    "confirmation step and reinstall existing packages as well",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package installation.",
    default=False,
)
def install(
    integrations: Tuple[str],
    ignore_integration: Tuple[str],
    force: bool = False,
    uv: bool = False,
) -> None:
    """Installs the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are installed using pip or uv.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        ignore_integration: Integrations to ignore explicitly (passed in
            separately).
        force: Force the installation of the required packages.
        uv: Use uv for package installation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error(
            "UV is not installed but the uv flag was passed in. Please install "
            "uv or remove the uv flag."
        )

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integration_set = set(integration_registry.integrations.keys())

        for i in ignore_integration:
            try:
                integration_set.remove(i)
            except KeyError:
                error(
                    f"Integration {i} does not exist. Available integrations: "
                    f"{list(integration_registry.integrations.keys())}"
                )
    else:
        integration_set = set(integrations)

    if sys.version_info.minor == 12 and "tensorflow" in integration_set:
        warning(
            "The TensorFlow integration is not yet compatible with Python "
            "3.12, thus its installation is skipped. Consider using a "
            "different version of Python and stay in touch for further updates."
        )
        integration_set.remove("tensorflow")

    if sys.version_info.minor == 12 and "deepchecks" in integration_set:
        warning(
            "The Deepchecks integration is not yet compatible with Python "
            "3.12, thus its installation is skipped. Consider using a "
            "different version of Python and stay in touch for further updates."
        )
        integration_set.remove("deepchecks")

    requirements = []
    integrations_to_install = []
    for integration_name in integration_set:
        try:
            if force or not integration_registry.is_installed(
                integration_name
            ):
                requirements += (
                    integration_registry.select_integration_requirements(
                        integration_name
                    )
                )
                integrations_to_install.append(integration_name)
            else:
                declare(
                    f"All required packages for integration "
                    f"'{integration_name}' are already installed."
                )
        except KeyError:
            warning(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            "Are you sure you want to install the following "
            "packages to the current environment?\n"
            f"{requirements}"
        )
    ):
        with console.status("Installing integrations..."):
            install_packages(requirements, use_uv=uv)


@integration.command(
    help="Uninstall the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the uninstallation of the required packages. This will skip "
    "the confirmation step",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package uninstallation.",
    default=False,
)
def uninstall(
    integrations: Tuple[str], force: bool = False, uv: bool = False
) -> None:
    """Uninstalls the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are uninstalled using pip or uv.

    Args:
        integrations: The name of the integration to uninstall the requirements
            for.
        force: Force the uninstallation of the required packages.
        uv: Use uv for package uninstallation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error("Package `uv` is not installed. Please install it and retry.")

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integrations = tuple(integration_registry.integrations.keys())

    requirements = []
    for integration_name in integrations:
        try:
            if integration_registry.is_installed(integration_name):
                requirements += (
                    integration_registry.select_uninstall_requirements(
                        integration_name
                    )
                )
            else:
                warning(
                    f"Requirements for integration '{integration_name}' "
                    f"already not installed."
                )
        except KeyError:
            warning(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            "Are you sure you want to uninstall the following "
            "packages from the current environment?\n"
            f"{requirements}"
        )
    ):
        for n in track(
            range(len(requirements)),
            description="Uninstalling integrations...",
        ):
            uninstall_package(requirements[n], use_uv=uv)


@integration.command(
    help="Upgrade the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the upgrade of the required packages. This will skip the "
    "confirmation step and re-upgrade existing packages as well",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package upgrade.",
    default=False,
)
def upgrade(
    integrations: Tuple[str],
    force: bool = False,
    uv: bool = False,
) -> None:
    """Upgrade the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are installed using pip or uv.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        force: Force the installation of the required packages.
        uv: Use uv for package installation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error("Package `uv` is not installed. Please install it and retry.")

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integrations = set(integration_registry.integrations.keys())

    requirements = []
    integrations_to_install = []
    for integration_name in integrations:
        try:
            if integration_registry.is_installed(integration_name):
                requirements += (
                    integration_registry.select_integration_requirements(
                        integration_name
                    )
                )
                integrations_to_install.append(integration_name)
            else:
                declare(
                    f"None of the required packages for integration "
                    f"'{integration_name}' are installed."
                )
        except KeyError:
            warning(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            f"Are you sure you want to upgrade the following "
            "packages to the current environment?\n"
            f"{requirements}"
        )
    ):
        with console.status("Upgrading integrations..."):
            install_packages(requirements, upgrade=True, use_uv=uv)
