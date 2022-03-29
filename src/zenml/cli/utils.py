#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
import datetime
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import click
from dateutil import tz
from rich import box, table
from rich.text import Text

from zenml.config.profile_config import ProfileConfiguration
from zenml.console import console
from zenml.constants import IS_DEBUG_ENV
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.secret import BaseSecretSchema
from zenml.stack import StackComponent

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.integrations.integration import IntegrationMeta


def title(text: str) -> None:
    """Echo a title formatted string on the CLI.

    Args:
      text: Input text string.
    """
    console.print(text.upper(), style="title")


def confirmation(text: str, *args: Any, **kwargs: Any) -> bool:
    """Echo a confirmation string on the CLI.

    Args:
      text: Input text string.
      *args: Args to be passed to click.confirm().
      **kwargs: Kwargs to be passed to click.confirm().

    Returns:
        Boolean based on user response.
    """
    # return Confirm.ask(text, console=console)
    return click.confirm(click.style(text, fg="yellow"), *args, **kwargs)


def declare(text: Union[str, Text]) -> None:
    """Echo a declaration on the CLI.

    Args:
      text: Input text string.
    """
    console.print(text, style="info")


def error(text: str) -> None:
    """Echo an error string on the CLI.

    Args:
      text: Input text string.

    Raises:
        click.ClickException: when called.
    """
    raise click.ClickException(message=click.style(text, fg="red", bold=True))
    # console.print(text, style="error")


def warning(text: str) -> None:
    """Echo a warning string on the CLI.

    Args:
      text: Input text string.
    """
    console.print(text, style="warning")


def pretty_print(obj: Any) -> None:
    """Pretty print an object on the CLI using `rich.print`.

    Args:
      obj: Any object with a __str__ method defined.
    # TODO: [LOW] check whether this needs to be converted to a string first
    # TODO: [LOW] use rich prettyprint for this instead
    """
    console.print(obj)


def print_table(obj: List[Dict[str, Any]]) -> None:
    """Prints the list of dicts in a table format. The input object should be a
    List of Dicts. Each item in that list represent a line in the Table. Each
    dict should have the same keys. The keys of the dict will be used as
    headers of the resulting table.

    Args:
      obj: A List containing dictionaries.
    """
    columns = {key.upper(): None for dict_ in obj for key in dict_.keys()}
    rich_table = table.Table(*columns.keys(), box=box.HEAVY_EDGE)

    for dict_ in obj:
        values = columns.copy()
        values.update(dict_)
        rich_table.add_row(*list(values.values()))

    if len(rich_table.columns) > 1:
        rich_table.columns[0].justify = "center"
    console.print(rich_table)


def format_integration_list(
    integrations: List[Tuple[str, "IntegrationMeta"]]
) -> List[Dict[str, str]]:
    """Formats a list of integrations into a List of Dicts. This list of dicts
    can then be printed in a table style using cli_utils.print_table."""
    list_of_dicts = []
    for name, integration_impl in integrations:
        is_installed = integration_impl.check_installation()  # type: ignore[attr-defined]
        list_of_dicts.append(
            {
                "INSTALLED": ":white_check_mark:" if is_installed else "",
                "INTEGRATION": name,
                "REQUIRED_PACKAGES": ", ".join(integration_impl.REQUIREMENTS),  # type: ignore[attr-defined]
            }
        )
    return list_of_dicts


def print_stack_component_list(
    components: List[StackComponent],
    active_component_name: Optional[str] = None,
) -> None:
    """Prints a table with configuration options for a list of stack components.

    If a component is active (its name matches the `active_component_name`),
    it will be highlighted in a separate table column.

    Args:
        components: List of stack components to print.
        active_component_name: Name of the component that is currently
            active.
    """
    configurations = []
    for component in components:
        is_active = component.name == active_component_name
        component_config = {
            "ACTIVE": ":point_right:" if is_active else "",
            **{
                key.upper(): str(value)
                for key, value in component.dict().items()
            },
        }
        configurations.append(component_config)
    print_table(configurations)


def print_stack_configuration(
    config: Dict[StackComponentType, str],
    active: bool,
    stack_name: str,
) -> None:
    """Prints the configuration options of a stack."""
    stack_caption = f"'{stack_name}' stack"
    if active:
        stack_caption += " (ACTIVE)"
    rich_table = table.Table(
        box=box.HEAVY_EDGE,
        title="Stack Configuration",
        caption=stack_caption,
        show_lines=True,
    )
    rich_table.add_column("COMPONENT_TYPE")
    rich_table.add_column("COMPONENT_NAME")
    items = ([typ.value, name] for typ, name in config.items())
    for item in items:
        rich_table.add_row(*item)

    # capitalize entries in first column
    rich_table.columns[0]._cells = [
        component.upper() for component in rich_table.columns[0]._cells  # type: ignore[union-attr]
    ]
    console.print(rich_table)


def print_stack_component_configuration(
    component: StackComponent, display_name: str, active_status: bool
) -> None:
    """Prints the configuration options of a stack component."""
    title = f"{component.type.value.upper()} Component Configuration"
    if active_status:
        title += " (ACTIVE)"
    rich_table = table.Table(
        box=box.HEAVY_EDGE,
        title=title,
        show_lines=True,
    )
    rich_table.add_column("COMPONENT_PROPERTY")
    rich_table.add_column("VALUE")
    items = component.dict().items()
    for item in items:
        rich_table.add_row(*[str(elem) for elem in item])

    # capitalize entries in first column
    rich_table.columns[0]._cells = [
        component.upper() for component in rich_table.columns[0]._cells  # type: ignore[union-attr]
    ]
    console.print(rich_table)


def print_active_profile() -> None:
    """Print active profile."""
    repo = Repository()
    scope = "local" if repo.root else "global"
    declare(
        f"Running with active profile: '{repo.active_profile_name}' ({scope})"
    )


def print_active_stack() -> None:
    """Print active stack."""
    repo = Repository()
    declare(f"Running with active stack: '{repo.active_stack_name}'")


def print_profile(
    profile: ProfileConfiguration,
    active: bool,
) -> None:
    """Prints the configuration options of a profile.

    Args:
        profile: Profile to print.
        active: Whether the profile is active.
        name: Name of the profile.
    """
    profile_title = f"'{profile.name}' Profile Configuration"
    if active:
        profile_title += " (ACTIVE)"

    rich_table = table.Table(
        box=box.HEAVY_EDGE,
        title=profile_title,
        show_lines=True,
    )
    rich_table.add_column("PROPERTY")
    rich_table.add_column("VALUE")
    items = profile.dict().items()
    for item in items:
        rich_table.add_row(*[str(elem) for elem in item])

    # capitalize entries in first column
    rich_table.columns[0]._cells = [
        component.upper() for component in rich_table.columns[0]._cells  # type: ignore[union-attr]
    ]
    console.print(rich_table)


def format_date(
    dt: datetime.datetime, format: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """Format a date into a string.

    Args:
      dt: Datetime object to be formatted.
      format: The format in string you want the datetime formatted to.

    Returns:
        Formatted string according to specification.
    """
    if dt is None:
        return ""
    # make sure this is UTC
    dt = dt.replace(tzinfo=tz.tzutc())

    if sys.platform != "win32":
        # On non-windows get local time zone.
        local_zone = tz.tzlocal()
        dt = dt.astimezone(local_zone)
    else:
        logger.warning("On Windows, all times are displayed in UTC timezone.")

    return dt.strftime(format)


def parse_unknown_options(args: List[str]) -> Dict[str, Any]:
    """Parse unknown options from the CLI.

    Args:
      args: A list of strings from the CLI.

    Returns:
        Dict of parsed args.
    """
    warning_message = (
        "Please provide args with a proper "
        "identifier as the key and the following structure: "
        '--custom_argument="value"'
    )

    assert all(a.startswith("--") for a in args), warning_message
    assert all(len(a.split("=")) == 2 for a in args), warning_message

    p_args = [a.lstrip("--").split("=") for a in args]

    assert all(k.isidentifier() for k, _ in p_args), warning_message

    r_args = {k: v for k, v in p_args}
    assert len(p_args) == len(r_args), "Replicated arguments!"

    return r_args


def install_packages(packages: List[str]) -> None:
    """Installs pypi packages into the current environment with pip"""
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
    ] + packages

    if not IS_DEBUG_ENV:
        command += [
            "-qqq",
            "--no-warn-conflicts",
        ]

    subprocess.check_call(command)


def uninstall_package(package: str) -> None:
    """Uninstalls pypi package from the current environment with pip"""
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            "-qqq",
            "-y",
            package,
        ]
    )


def pretty_print_secret(
    secret: BaseSecretSchema, hide_secret: bool = True
) -> None:
    """Given a secret set print all key value pairs associated with the secret

    Args:
        secret: Secret of type BaseSecretSchema
        hide_secret: boolean that configures if the secret values are shown
            on the CLI
    """
    stack_dicts = [
        {
            "SECRET_NAME": secret.name,
            "SECRET_KEY": key,
            "SECRET_VALUE": "***" if hide_secret else value,
        }
        for key, value in secret.content.items()
    ]
    print_table(stack_dicts)


def print_secrets(secrets: List[str]) -> None:
    """Prints the configuration options of a stack.

    Args:
        secrets: List of secrets
    """
    rich_table = table.Table(
        box=box.HEAVY_EDGE,
        title="Secrets",
        show_lines=True,
    )
    rich_table.add_column("SECRET_NAME")
    secrets.sort()
    for item in secrets:
        rich_table.add_row(item)

    console.print(rich_table)
