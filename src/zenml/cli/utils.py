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
import functools
import subprocess
import sys
from typing import Any, Callable, Dict, List, TypeVar, cast

import click
from dateutil import tz
from tabulate import tabulate

from zenml.logger import get_logger
from zenml.stack import StackComponent

logger = get_logger(__name__)


def title(text: str) -> None:
    """Echo a title formatted string on the CLI.

    Args:
      text: Input text string.
    """
    click.echo(click.style(text.upper(), fg="cyan", bold=True, underline=True))


def confirmation(text: str, *args: Any, **kwargs: Any) -> bool:
    """Echo a confirmation string on the CLI.

    Args:
      text: Input text string.
      *args: Args to be passed to click.confirm().
      **kwargs: Kwargs to be passed to click.confirm().

    Returns:
        Boolean based on user response.
    """
    return click.confirm(click.style(text, fg="yellow"), *args, **kwargs)


def declare(text: str) -> None:
    """Echo a declaration on the CLI.

    Args:
      text: Input text string.
    """
    click.echo(click.style(text, fg="green"))


def error(text: str) -> None:
    """Echo an error string on the CLI.

    Args:
      text: Input text string.

    Raises:
        click.ClickException: when called.
    """
    raise click.ClickException(message=click.style(text, fg="red", bold=True))


def warning(text: str) -> None:
    """Echo a warning string on the CLI.

    Args:
      text: Input text string.
    """
    click.echo(click.style(text, fg="yellow", bold=True))


def pretty_print(obj: Any) -> None:
    """Pretty print an object on the CLI.

    Args:
      obj: Any object with a __str__ method defined.
    """
    click.echo(str(obj))


def print_table(obj: List[Dict[str, Any]]) -> None:
    """Echoes the list of dicts in a table format. The input object should be a
    List of Dicts. Each item in that list represent a line in the Table. Each
    dict should have the same keys. The keys of the dict will be used as
    headers of the resulting table.

    Args:
      obj: A List containing dictionaries.
    """
    click.echo(tabulate(obj, headers="keys"))


def print_stack_component_list(
    components: List[StackComponent], active_component_name: str
) -> None:
    """Prints a table with configuration options for a list of stack components.

    If a component is active (its name matches the `active_component_name`),
    it will be highlighted in a separate table column.

    Args:
        components: List of stack components to print.
        active_component_name: Name of the component that is currently active.
    """
    configurations = []
    for component in components:
        is_active = component.name == active_component_name
        component_config = {
            "ACTIVE": "*" if is_active else "",
            **{key.upper(): value for key, value in component.dict().items()},
        }
        configurations.append(component_config)

    print_table(configurations)


def print_stack_component_configuration(component: StackComponent) -> None:
    """Prints the configuration options of a stack component."""
    declare(f"NAME: {component.name}")
    for key, value in component.dict(exclude={"name"}).items():
        declare(f"{key.upper()}: {value}")


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


F = TypeVar("F", bound=Callable[..., Any])


def activate_integrations(func: F) -> F:
    """Decorator that activates all ZenML integrations."""

    @functools.wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        """Inner decorator function"""
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()
        return func(*args, **kwargs)

    return cast(F, _wrapper)


def install_package(package: str) -> None:
    """Installs pypi package into the current environment with pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def uninstall_package(package: str) -> None:
    """Uninstalls pypi package from the current environment with pip"""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "uninstall", "-y", package]
    )
