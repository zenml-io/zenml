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
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    TypeVar,
    cast,
)

import click
from dateutil import tz
from tabulate import tabulate

from zenml.cli import utils as cli_utils
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.core.base_component import BaseComponent


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
        click.ClickException when called.
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


def format_component_list(
    component_list: Mapping[str, "BaseComponent"], active_component: str
) -> List[Dict[str, str]]:
    """Formats a list of components into a List of Dicts. This list of dicts
    can then be printed in a table style using cli_utils.print_table.

    Args:
        component_list: The component_list is a mapping of component key to component class with its relevant attributes
        active_component: The component that is currently active
    Returns:
        list_of_dicts: A list of all components with each component as a dict
    """
    list_of_dicts = []
    for key, c in component_list.items():
        # Make sure that the `name` key is not taken in the component dict
        # In case `name` exists, it is replaced inplace with `component_name`
        component_dict = {
            "COMPONENT_NAME" if k == "name" else k.upper(): v
            for k, v in c.dict(exclude={"_superfluous_options"}).items()
        }

        data = {"ACTIVE": "*" if key == active_component else "", "NAME": key}
        data.update(component_dict)
        list_of_dicts.append(data)
    return list_of_dicts


def print_component_properties(properties: Dict[str, str]) -> None:
    """Prints the properties of a component.

    Args:
        properties: A dictionary of properties.
    """
    for key, value in properties.items():
        cli_utils.declare(f"{key.upper()}: {value}")


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
