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
"""Utility functions for the CLI."""

import contextlib
import csv
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from functools import partial
from typing import (
    IO,
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
)
from uuid import UUID

import click
import yaml
from pydantic import BaseModel, SecretStr
from rich import box, table
from rich.console import Console
from rich.emoji import Emoji, NoEmoji
from rich.markdown import Markdown
from rich.padding import Padding
from rich.prompt import Confirm, Prompt
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table

from zenml.client import Client
from zenml.console import console, zenml_style_defaults
from zenml.constants import (
    ENV_ZENML_CLI_COLUMN_WIDTH,
    ENV_ZENML_DEFAULT_OUTPUT,
    FILTERING_DATETIME_FORMAT,
    IS_DEBUG_ENV,
    handle_int_env_var,
)
from zenml.deployers.utils import (
    get_deployment_input_schema,
    get_deployment_invocation_example,
    get_deployment_output_schema,
)
from zenml.enums import (
    DeploymentStatus,
    GenericFilterOps,
    ServiceState,
    StackComponentType,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    RegisteredModel,
    RegistryModelVersion,
)
from zenml.models import (
    BaseFilter,
    BaseIdentifiedResponse,
    BoolFilter,
    NumericFilter,
    Page,
    ServiceConnectorRequirements,
    StrFilter,
    UserResponse,
    UserScopedResponse,
    UUIDFilter,
)
from zenml.models.v2.base.filter import FilterGenerator
from zenml.services import BaseService
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig
from zenml.utils import secret_utils
from zenml.utils.package_utils import requirement_installed
from zenml.utils.time_utils import expires_in
from zenml.utils.typing_utils import get_origin, is_union
from zenml.utils.uuid_utils import is_valid_uuid

if TYPE_CHECKING:
    from uuid import UUID

    from rich.text import Text

    from zenml.enums import ExecutionStatus
    from zenml.integrations.integration import Integration
    from zenml.model_deployers import BaseModelDeployer
    from zenml.models import (
        AuthenticationMethodModel,
        ComponentResponse,
        DeploymentResponse,
        FlavorResponse,
        PipelineRunResponse,
        PipelineSnapshotResponse,
        ProjectResponse,
        ResourceTypeModel,
        ServiceConnectorRequest,
        ServiceConnectorResourcesModel,
        ServiceConnectorResponse,
        ServiceConnectorTypeModel,
        StackResponse,
        UserResponse,
    )
    from zenml.stack import Stack


logger = get_logger(__name__)

AnyResponse = TypeVar(
    "AnyResponse", bound=BaseIdentifiedResponse[Any, Any, Any]
)
OutputFormat = Literal["table", "json", "yaml", "csv", "tsv"]

MAX_ARGUMENT_VALUE_SIZE = 10240


T = TypeVar("T", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]


def title(text: str) -> None:
    """Echo a title formatted string on the CLI.

    Args:
        text: Input text string.
    """
    console.print(text.upper(), style=zenml_style_defaults["title"])


def confirmation(text: str, *args: Any, **kwargs: Any) -> bool:
    """Echo a confirmation string on the CLI.

    Args:
        text: Input text string.
        *args: Args to be passed to click.confirm().
        **kwargs: Kwargs to be passed to click.confirm().

    Returns:
        Boolean based on user response.
    """
    return Confirm.ask(text, console=console)


def declare(
    text: Union[str, "Text"],
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    **kwargs: Any,
) -> None:
    """Echo a declaration on the CLI.

    Args:
        text: Input text string.
        bold: Optional boolean to bold the text.
        italic: Optional boolean to italicize the text.
        **kwargs: Optional kwargs to be passed to console.print().
    """
    base_style = zenml_style_defaults["info"]
    style = Style.chain(base_style, Style(bold=bold, italic=italic))
    console.print(text, style=style, **kwargs)


def error(text: str) -> NoReturn:
    """Echo an error string on the CLI.

    Args:
        text: Input text string.

    Raises:
        StyledClickException: when called.
    """
    error_prefix = click.style("Error: ", fg="red", bold=True)
    error_message = click.style(text, fg="red", bold=False)

    class StyledClickException(click.ClickException):
        def show(self, file: Optional[IO[Any]] = None) -> None:
            if file is None:
                file = click.get_text_stream("stderr")
            click.echo(self.message, file=file)

    raise StyledClickException(message=error_prefix + error_message)


def exception(exception: Exception) -> NoReturn:
    """Echo an exception string on the CLI.

    Args:
        exception: Input exception.
    """
    # KeyError add quotes around their error message to handle the case when
    # someone tried to fetch something with the key '' (empty string). In all
    # other cases where the key is not empty however, this adds unnecessary
    # quotes around the error message, which this function removes.
    if (
        isinstance(exception, KeyError)
        and len(exception.args) == 1
        # If the exception is a KeyError with an empty string as the argument,
        # we use the default string representation which will print ''
        and exception.args[0]
        and isinstance(exception.args[0], str)
    ):
        error_message = exception.args[0]
    else:
        error_message = str(exception)

    error(error_message)


def warning(
    text: str,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    **kwargs: Any,
) -> None:
    """Echo a warning string on the CLI.

    Args:
        text: Input text string.
        bold: Optional boolean to bold the text.
        italic: Optional boolean to italicize the text.
        **kwargs: Optional kwargs to be passed to console.print().
    """
    base_style = zenml_style_defaults["warning"]
    style = Style.chain(base_style, Style(bold=bold, italic=italic))
    console.print(text, style=style, **kwargs)


def success(
    text: str,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    **kwargs: Any,
) -> None:
    """Echo a success string on the CLI.

    Args:
        text: Input text string.
        bold: Optional boolean to bold the text.
        italic: Optional boolean to italicize the text.
        **kwargs: Optional kwargs to be passed to console.print().
    """
    base_style = zenml_style_defaults["success"]
    style = Style.chain(base_style, Style(bold=bold, italic=italic))
    console.print(text, style=style, **kwargs)


def print_table(
    obj: List[Dict[str, Any]],
    title: Optional[str] = None,
    caption: Optional[str] = None,
    columns: Optional[Dict[str, Union[table.Column, str]]] = None,
    column_aliases: Optional[Dict[str, str]] = None,
    **kwargs: table.Column,
) -> None:
    """Prints a list of dicts as a table.

    Args:
        obj: A List containing dictionaries.
        title: Title of the table.
        caption: Caption of the table.
        columns: Optional mapping of data keys to column configurations.
            Values can be either a rich Column object (uses .header for display)
            or a string (used directly as the header). Keys not in this mapping
            will use the uppercased key as the header.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.
        **kwargs: Deprecated. Use `columns` dict instead. Kept for backward
            compatibility.
    """
    all_columns: Dict[str, Union[table.Column, str]] = dict(kwargs)
    if columns:
        all_columns.update(columns)

    data = obj
    if all_columns:
        data = []
        for row in obj:
            new_row = {}
            for k, v in row.items():
                col_config = all_columns.get(k)
                if col_config is None:
                    header = k.upper()
                elif isinstance(col_config, table.Column):
                    header = str(col_config.header)
                else:
                    header = str(col_config)
                new_row[header] = v
            data.append(new_row)

    if not data:
        return

    print(
        _render_table(
            data, title=title, caption=caption, column_aliases=column_aliases
        ),
        end="",
    )


def print_pydantic_models(
    models: Union[Page[T], List[T]],
    columns: Optional[List[str]] = None,
    exclude_columns: Optional[List[str]] = None,
    active_models: Optional[List[T]] = None,
    show_active: bool = False,
    column_aliases: Optional[Dict[str, str]] = None,
) -> None:
    """Prints the list of Pydantic models in a table.

    Args:
        models: List of Pydantic models that will be represented as a row in
            the table.
        columns: Optionally specify subset and order of columns to display.
        exclude_columns: Optionally specify columns to exclude. (Note: `columns`
            takes precedence over `exclude_columns`.)
        active_models: Optional list of active models of the given type T.
        show_active: Flag to decide whether to append the active model on the
            top of the list.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.
    """
    if exclude_columns is None:
        exclude_columns = list()

    show_active_column = True
    if active_models is None:
        show_active_column = False
        active_models = list()

    def __dictify(model: T) -> Dict[str, str]:
        """Helper function to map over the list to turn Models into dicts.

        Args:
            model: Pydantic model.

        Returns:
            Dict of model attributes.
        """
        include_columns = _extract_model_columns(
            model=model, columns=columns, exclude_columns=exclude_columns
        )

        items: Dict[str, Any] = {}

        for k in include_columns:
            value = getattr(model, k)
            items[k] = _format_response_value(value)

        if not active_models and not show_active:
            return items

        marker = "active"
        if marker in items:
            marker = "current"
        if active_models is not None and show_active_column:
            return {
                marker: (
                    "[green]●[/green]"
                    if any(model.id == a.id for a in active_models)
                    else "-"
                ),
                **items,
            }

        return items

    active_ids = [a.id for a in active_models]
    if isinstance(models, Page):
        table_items = list(models.items)

        if show_active:
            for active_model in active_models:
                if active_model.id not in [i.id for i in table_items]:
                    table_items.append(active_model)

            table_items = [i for i in table_items if i.id in active_ids] + [
                i for i in table_items if i.id not in active_ids
            ]

        print_table(
            [__dictify(model) for model in table_items],
            column_aliases=column_aliases,
        )
        print_page_info(models)
    else:
        table_items = list(models)

        if show_active:
            for active_model in active_models:
                if active_model.id not in [i.id for i in table_items]:
                    table_items.append(active_model)

            table_items = [i for i in table_items if i.id in active_ids] + [
                i for i in table_items if i.id not in active_ids
            ]

        print_table(
            [__dictify(model) for model in table_items],
            column_aliases=column_aliases,
        )


def print_pydantic_model(
    title: str,
    model: BaseModel,
    exclude_columns: Optional[AbstractSet[str]] = None,
    columns: Optional[AbstractSet[str]] = None,
) -> None:
    """Prints a single Pydantic model in a table.

    Args:
        title: Title of the table.
        model: Pydantic model that will be represented as a row in the table.
        exclude_columns: Optionally specify columns to exclude.
        columns: Optionally specify subset and order of columns to display.
    """
    include_columns = _extract_model_columns(
        model=model,
        columns=list(columns) if columns else None,
        exclude_columns=list(exclude_columns) if exclude_columns else None,
    )

    items: Dict[str, Any] = {}
    for k in include_columns:
        value = getattr(model, k)
        items[k] = _format_response_value(value)

    _print_key_value_table(items, title=title)


def format_integration_list(
    integrations: List[Tuple[str, Type["Integration"]]],
) -> List[Dict[str, str]]:
    """Formats a list of integrations into a List of Dicts.

    This list of dicts can then be printed in a table style using
    cli_utils.print_table.

    Args:
        integrations: List of tuples containing the name of the integration and
            the integration metadata.

    Returns:
        List of Dicts containing the name of the integration and the integration
    """
    list_of_dicts = []
    for name, integration_impl in integrations:
        is_installed = integration_impl.check_installation()
        list_of_dicts.append(
            {
                "INSTALLED": ":white_check_mark:" if is_installed else ":x:",
                "INTEGRATION": name,
                "REQUIRED_PACKAGES": ", ".join(
                    integration_impl.get_requirements()
                ),
            }
        )
    return list_of_dicts


def print_stack_configuration(stack: "StackResponse", active: bool) -> None:
    """Prints the configuration options of a stack.

    Args:
        stack: Instance of a stack model.
        active: Whether the stack is active.
    """
    stack_caption = f"'{stack.name}' stack"
    if active:
        stack_caption += " (ACTIVE)"
    rich_table = table.Table(
        box=box.ROUNDED,
        title="Stack Configuration",
        caption=stack_caption,
        show_lines=True,
    )
    rich_table.add_column("COMPONENT_TYPE", overflow="fold")
    rich_table.add_column("COMPONENT_NAME", overflow="fold")
    for component_type, components in stack.components.items():
        rich_table.add_row(component_type, components[0].name)

    rich_table.columns[0]._cells = [
        component.upper()  # type: ignore[union-attr]
        for component in rich_table.columns[0]._cells
    ]
    console.print(rich_table)

    if not stack.labels:
        declare("No labels are set for this stack.")
    else:
        rich_table = table.Table(
            box=box.ROUNDED,
            title="Labels",
            show_lines=True,
        )
        rich_table.add_column("LABEL")
        rich_table.add_column("VALUE", overflow="fold")

        for label, value in stack.labels.items():
            rich_table.add_row(label, str(value))

        console.print(rich_table)

    declare(
        f"Stack '{stack.name}' with id '{stack.id}' is "
        f"{f'owned by user {stack.user.name}.' if stack.user else 'unowned.'}"
    )


def print_flavor_list(flavors: Page["FlavorResponse"]) -> None:
    """Prints the list of flavors.

    Args:
        flavors: List of flavors to print.
    """
    flavor_table = []
    for f in flavors.items:
        flavor_table.append(
            {
                "FLAVOR": f.name,
                "INTEGRATION": f.integration,
                "SOURCE": f.source,
                "CONNECTOR TYPE": f.connector_type or "",
                "RESOURCE TYPE": f.connector_resource_type or "",
            }
        )

    print_table(flavor_table)


def print_stack_component_configuration(
    component: "ComponentResponse",
    active_status: bool,
    connector_requirements: Optional[ServiceConnectorRequirements] = None,
) -> None:
    """Prints the configuration options of a stack component.

    Args:
        component: The stack component to print.
        active_status: Whether the stack component is active.
        connector_requirements: Connector requirements for the component, taken
            from the component flavor. Only needed if the component has a
            connector.
    """
    user_name = _get_user_name(component.user)

    declare(
        f"{component.type.value.title()} '{component.name}' of flavor "
        f"'{component.flavor_name}' with id '{component.id}' is owned by "
        f"user '{user_name}'."
    )

    if len(component.configuration) == 0:
        declare("No configuration options are set for this component.")

    else:
        title_ = (
            f"'{component.name}' {component.type.value.upper()} "
            f"Component Configuration"
        )

        if active_status:
            title_ += " (ACTIVE)"
        rich_table = table.Table(
            box=box.ROUNDED,
            title=title_,
            show_lines=True,
        )
        rich_table.add_column("COMPONENT_PROPERTY")
        rich_table.add_column("VALUE", overflow="fold")

        items = component.configuration.items()
        for item in items:
            elements = []
            for idx, elem in enumerate(item):
                if idx == 0:
                    elements.append(f"{elem.upper()}")
                else:
                    elements.append(str(elem))
            rich_table.add_row(*elements)

        console.print(rich_table)

    if not component.labels:
        declare("No labels are set for this component.")
    else:
        rich_table = table.Table(
            box=box.ROUNDED,
            title="Labels",
            show_lines=True,
        )
        rich_table.add_column("LABEL")
        rich_table.add_column("VALUE", overflow="fold")

        for label, value in component.labels.items():
            rich_table.add_row(label, str(value))

        console.print(rich_table)

    if not component.connector:
        declare("No connector is set for this component.")
    else:
        rich_table = table.Table(
            box=box.ROUNDED,
            title="Service Connector",
            show_lines=True,
        )
        rich_table.add_column("PROPERTY")
        rich_table.add_column("VALUE", overflow="fold")

        resource_type = (
            connector_requirements.resource_type
            if connector_requirements
            else component.connector.resource_types[0]
        )

        connector_dict = {
            "ID": str(component.connector.id),
            "NAME": component.connector.name,
            "TYPE": component.connector.type,
            "RESOURCE TYPE": resource_type,
            "RESOURCE NAME": component.connector_resource_id
            or component.connector.resource_id
            or "N/A",
        }

        for label, value in connector_dict.items():
            rich_table.add_row(label, value)

        console.print(rich_table)


def expand_argument_value_from_file(name: str, value: str) -> str:
    """Expands the value of an argument pointing to a file into the contents of that file.

    Args:
        name: Name of the argument. Used solely for logging purposes.
        value: The value of the argument. This is to be interpreted as a
            filename if it begins with a `@` character.

    Returns:
        The argument value expanded into the contents of the file, if the
        argument value begins with a `@` character. Otherwise, the argument
        value is returned unchanged.

    Raises:
        ValueError: If the argument value points to a file that doesn't exist,
            that cannot be read, or is too long(i.e. exceeds
            `MAX_ARGUMENT_VALUE_SIZE` bytes).
    """
    if value.startswith("@@"):
        return value[1:]
    if not value.startswith("@"):
        return value
    filename = os.path.abspath(os.path.expanduser(value[1:]))
    logger.info(
        f"Expanding argument value `{name}` to contents of file `{filename}`."
    )
    if not os.path.isfile(filename):
        raise ValueError(
            f"Could not load argument '{name}' value: file "
            f"'{filename}' does not exist or is not readable."
        )
    try:
        if os.path.getsize(filename) > MAX_ARGUMENT_VALUE_SIZE:
            raise ValueError(
                f"Could not load argument '{name}' value: file "
                f"'{filename}' is too large (max size is "
                f"{MAX_ARGUMENT_VALUE_SIZE} bytes)."
            )

        with open(filename, "r") as f:
            return f.read()
    except OSError as e:
        raise ValueError(
            f"Could not load argument '{name}' value: file "
            f"'{filename}' could not be accessed: {str(e)}"
        )


def convert_structured_str_to_dict(string: str) -> Dict[str, str]:
    """Convert a structured string (JSON or YAML) into a dict.

    Examples:
        >>> convert_structured_str_to_dict('{"location": "Nevada", "aliens":"many"}')
        {'location': 'Nevada', 'aliens': 'many'}
        >>> convert_structured_str_to_dict('location: Nevada \\naliens: many')
        {'location': 'Nevada', 'aliens': 'many'}
        >>> convert_structured_str_to_dict("{'location': 'Nevada', 'aliens': 'many'}")
        {'location': 'Nevada', 'aliens': 'many'}

    Args:
        string: JSON or YAML string value

    Returns:
        dict_: dict from structured JSON or YAML str
    """
    try:
        dict_: Dict[str, str] = json.loads(string)
        return dict_
    except ValueError:
        pass

    try:
        # Here, Dict type in str is implicitly supported by yaml.safe_load()
        dict_ = yaml.safe_load(string)
        return dict_
    except yaml.YAMLError:
        pass

    error(
        f"Invalid argument: '{string}'. Please provide the value in JSON or YAML format."
    )


def parse_name_and_extra_arguments(
    args: List[str],
    expand_args: bool = False,
    name_mandatory: bool = True,
) -> Tuple[Optional[str], Dict[str, str]]:
    """Parse a name and extra arguments from the CLI.

    This is a utility function used to parse a variable list of optional CLI
    arguments of the form `--key=value` that must also include one mandatory
    free-form name argument. There is no restriction as to the order of the
    arguments.

    Examples:
        >>> parse_name_and_extra_arguments(['foo']])
        ('foo', {})
        >>> parse_name_and_extra_arguments(['foo', '--bar=1'])
        ('foo', {'bar': '1'})
        >>> parse_name_and_extra_arguments(['--bar=1', 'foo', '--baz=2'])
        ('foo', {'bar': '1', 'baz': '2'})
        >>> parse_name_and_extra_arguments(['--bar=1'])
        Traceback (most recent call last):
            ...
            ValueError: Missing required argument: name

    Args:
        args: A list of command line arguments from the CLI.
        expand_args: Whether to expand argument values into the contents of the
            files they may be pointing at using the special `@` character.
        name_mandatory: Whether the name argument is mandatory.

    Returns:
        The name and a dict of parsed args.
    """
    name: Optional[str] = None
    # The name was not supplied as the first argument, we have to
    # search the other arguments for the name.
    for i, arg in enumerate(args):
        if not arg:
            # Skip empty arguments.
            continue
        if arg.startswith("--"):
            continue
        name = args.pop(i)
        break
    else:
        if name_mandatory:
            error(
                "A name must be supplied. Please see the command help for more "
                "information."
            )

    message = (
        "Please provide args with a proper "
        "identifier as the key and the following structure: "
        '--custom_argument="value"'
    )
    args_dict: Dict[str, str] = {}
    for a in args:
        if not a:
            # Skip empty arguments.
            continue
        if not a.startswith("--") or "=" not in a:
            error(f"Invalid argument: '{a}'. {message}")
        key, value = a[2:].split("=", maxsplit=1)
        if not key.isidentifier():
            error(f"Invalid argument: '{a}'. {message}")
        args_dict[key] = value

    if expand_args:
        args_dict = {
            k: expand_argument_value_from_file(k, v)
            for k, v in args_dict.items()
        }

    return name, args_dict


def validate_keys(key: str) -> None:
    """Validates key if it is a valid python string.

    Args:
        key: key to validate
    """
    if not key.isidentifier():
        error("Please provide args with a proper identifier as the key.")


def prompt_configuration(
    config_schema: Dict[str, Any],
    show_secrets: bool = False,
    existing_config: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Prompt the user for configuration values using the provided schema.

    Args:
        config_schema: The configuration schema.
        show_secrets: Whether to show secrets in the terminal.
        existing_config: The existing configuration values.

    Returns:
        The configuration values provided by the user.
    """
    is_update = False
    if existing_config is not None:
        is_update = True
    existing_config = existing_config or {}

    config_dict = {}
    for attr_name, attr_schema in config_schema.get("properties", {}).items():
        title = attr_schema.get("title", attr_name)
        attr_type_name = attr_type = attr_schema.get("type", "string")
        if attr_type == "array":
            attr_type_name = "list (CSV or JSON)"
        title = f"[{attr_name}] {title}"
        required = attr_name in config_schema.get("required", [])
        hidden = attr_schema.get("format", "") == "password"
        subtitles: List[str] = []
        subtitles.append(attr_type_name)
        if hidden:
            subtitles.append("secret")
        if required:
            subtitles.append("required")
        else:
            subtitles.append("optional")
        if subtitles:
            title += f" {{{', '.join(subtitles)}}}"

        existing_value = existing_config.get(attr_name)
        if is_update:
            if existing_value:
                if isinstance(existing_value, SecretStr):
                    existing_value = existing_value.get_secret_value()
                if hidden and not show_secrets:
                    title += " is currently set to: [HIDDEN]"
                else:
                    if attr_type == "array":
                        existing_value = json.dumps(existing_value)
                    title += f" is currently set to: '{existing_value}'"
            else:
                title += " is not currently set"

            click.echo(title)

            if existing_value:
                title = (
                    "Please enter a new value or press Enter to keep the "
                    "existing one"
                )
            elif required:
                title = "Please enter a new value"
            else:
                title = "Please enter a new value or press Enter to skip it"

        while True:
            # Ask the user to enter a value for the attribute
            value = click.prompt(
                title,
                type=str,
                hide_input=hidden and not show_secrets,
                default=existing_value or ("" if not required else None),
                show_default=False,
            )
            if not value:
                if required:
                    warning(
                        f"The attribute '{title}' is mandatory. "
                        "Please enter a non-empty value."
                    )
                    continue
                else:
                    value = None
                    break
            else:
                break

        if (
            is_update
            and value is not None
            and value == existing_value
            and not required
        ):
            confirm = click.confirm(
                "You left this optional attribute unchanged. Would you "
                "like to remove its value instead?",
                default=False,
            )
            if confirm:
                value = None

        if value:
            config_dict[attr_name] = value

    return config_dict


def install_packages(
    packages: List[str],
    upgrade: bool = False,
    use_uv: bool = False,
) -> None:
    """Installs pypi packages into the current environment with pip or uv.

    When using with `uv`, a virtual environment is required.

    Args:
        packages: List of packages to install.
        upgrade: Whether to upgrade the packages if they are already installed.
        use_uv: Whether to use uv for package installation.

    Raises:
        e: If the package installation fails.
    """
    if "neptune" in packages:
        declare(
            "Uninstalling legacy `neptune-client` package to avoid version "
            "conflicts with new `neptune` package..."
        )
        uninstall_package("neptune-client")

    if "prodigy" in packages:
        packages.remove("prodigy")
        declare(
            "The `prodigy` package should be installed manually using your "
            "license key. Please visit https://prodi.gy/docs/install for more "
            "information."
        )
    if not packages:
        # if user only tried to install prodigy, we can
        # just return without doing anything
        return

    if use_uv and not requirement_installed("uv"):
        # If uv is installed globally, don't run as a python module
        command = []
    else:
        command = [sys.executable, "-m"]

    command += ["uv", "pip", "install"] if use_uv else ["pip", "install"]

    if upgrade:
        command += ["--upgrade"]

    command += packages

    if not IS_DEBUG_ENV:
        quiet_flag = "-q" if use_uv else "-qqq"
        command.append(quiet_flag)
        if not use_uv:
            command.append("--no-warn-conflicts")

    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        if (
            use_uv
            and "Failed to locate a virtualenv or Conda environment" in str(e)
        ):
            error(
                "Failed to locate a virtualenv or Conda environment. "
                "When using uv, a virtual environment is required. "
                "Run `uv venv` to create a virtualenv and retry."
            )
        else:
            raise e


def uninstall_package(package: str, use_uv: bool = False) -> None:
    """Uninstalls pypi package from the current environment with pip or uv.

    Args:
        package: The package to uninstall.
        use_uv: Whether to use uv for package uninstallation.
    """
    if use_uv and not requirement_installed("uv"):
        command = []
    else:
        command = [sys.executable, "-m"]

    command += (
        ["uv", "pip", "uninstall", "-q"]
        if use_uv
        else ["pip", "uninstall", "-y", "-qqq"]
    )
    command += [package]

    subprocess.check_call(command)


def is_uv_installed() -> bool:
    """Check if uv is installed.

    Returns:
        True if uv is installed, False otherwise.
    """
    return shutil.which("uv") is not None


def is_pip_installed() -> bool:
    """Check if pip is installed in the current environment.

    Returns:
        True if pip is installed, False otherwise.
    """
    return requirement_installed("pip")


def pretty_print_secret(
    secret: Dict[str, str],
    hide_secret: bool = True,
) -> None:
    """Print all key-value pairs associated with a secret.

    Args:
        secret: Secret values to print.
        hide_secret: boolean that configures if the secret values are shown
            on the CLI
    """
    title: Optional[str] = None

    def get_secret_value(value: Any) -> str:
        if value is None:
            return ""
        return "***" if hide_secret else str(value)

    stack_dicts = [
        {
            "SECRET_KEY": key,
            "SECRET_VALUE": get_secret_value(value),
        }
        for key, value in secret.items()
    ]

    print_table(stack_dicts, title=title)


def get_service_state_emoji(state: "ServiceState") -> str:
    """Get the rich emoji representing the operational state of a Service.

    Args:
        state: Service state to get emoji for.

    Returns:
        String representing the emoji.
    """
    from zenml.enums import ServiceState

    if state == ServiceState.ACTIVE:
        return ":white_check_mark:"
    if state == ServiceState.INACTIVE:
        return ":pause_button:"
    if state == ServiceState.ERROR:
        return ":heavy_exclamation_mark:"
    if state == ServiceState.PENDING_STARTUP:
        return ":hourglass:"
    if state == ServiceState.SCALED_TO_ZERO:
        return ":chart_decreasing:"
    return ":hourglass_not_done:"


def pretty_print_model_deployer(
    model_services: List["BaseService"], model_deployer: "BaseModelDeployer"
) -> None:
    """Given a list of served_models, print all associated key-value pairs.

    Args:
        model_services: list of model deployment services
        model_deployer: Active model deployer
    """
    model_service_dicts = []
    for model_service in model_services:
        dict_uuid = str(model_service.uuid)
        dict_pl_name = model_service.config.pipeline_name
        dict_pl_stp_name = model_service.config.pipeline_step_name
        dict_model_name = model_service.config.model_name
        type = model_service.SERVICE_TYPE.type
        flavor = model_service.SERVICE_TYPE.flavor
        model_service_dicts.append(
            {
                "STATUS": get_service_state_emoji(model_service.status.state),
                "UUID": dict_uuid,
                "TYPE": type,
                "FLAVOR": flavor,
                "PIPELINE_NAME": dict_pl_name,
                "PIPELINE_STEP_NAME": dict_pl_stp_name,
                "MODEL_NAME": dict_model_name,
            }
        )
    print_table(
        model_service_dicts, UUID=table.Column(header="UUID", min_width=36)
    )


def pretty_print_registered_model_table(
    registered_models: List["RegisteredModel"],
) -> None:
    """Given a list of registered_models, print all associated key-value pairs.

    Args:
        registered_models: list of registered models
    """
    registered_model_dicts = [
        {
            "NAME": registered_model.name,
            "DESCRIPTION": registered_model.description,
            "METADATA": registered_model.metadata,
        }
        for registered_model in registered_models
    ]
    print_table(
        registered_model_dicts, UUID=table.Column(header="UUID", min_width=36)
    )


def pretty_print_model_version_table(
    model_versions: List["RegistryModelVersion"],
) -> None:
    """Given a list of model_versions, print all associated key-value pairs.

    Args:
        model_versions: list of model versions
    """
    model_version_dicts = [
        {
            "NAME": model_version.registered_model.name,
            "MODEL_VERSION": model_version.version,
            "VERSION_DESCRIPTION": model_version.description,
            "METADATA": (
                model_version.metadata.model_dump()
                if model_version.metadata
                else {}
            ),
        }
        for model_version in model_versions
    ]
    print_table(
        model_version_dicts, UUID=table.Column(header="UUID", min_width=36)
    )


def pretty_print_model_version_details(
    model_version: "RegistryModelVersion",
) -> None:
    """Given a model_version, print all associated key-value pairs.

    Args:
        model_version: model version
    """
    title_ = f"Properties of model `{model_version.registered_model.name}` version `{model_version.version}`"

    rich_table = table.Table(
        box=None,
        title=title_,
        show_lines=False,
    )
    rich_table.add_column("MODEL VERSION PROPERTY", overflow="fold")
    rich_table.add_column("VALUE", overflow="fold")
    model_version_info = {
        "REGISTERED_MODEL_NAME": model_version.registered_model.name,
        "VERSION": model_version.version,
        "VERSION_DESCRIPTION": model_version.description,
        "CREATED_AT": (
            str(model_version.created_at)
            if model_version.created_at
            else "N/A"
        ),
        "UPDATED_AT": (
            str(model_version.last_updated_at)
            if model_version.last_updated_at
            else "N/A"
        ),
        "METADATA": (
            model_version.metadata.model_dump()
            if model_version.metadata
            else {}
        ),
        "MODEL_SOURCE_URI": model_version.model_source_uri,
        "STAGE": model_version.stage.value,
    }

    for item in model_version_info.items():
        rich_table.add_row(*[str(elem) for elem in item])

    rich_table.columns[0]._cells = [
        component.upper()  # type: ignore[union-attr]
        for component in rich_table.columns[0]._cells
    ]
    console.print(rich_table)


def print_served_model_configuration(
    model_service: "BaseService", model_deployer: "BaseModelDeployer"
) -> None:
    """Prints the configuration of a model_service.

    Args:
        model_service: Specific service instance to
        model_deployer: Active model deployer
    """
    title_ = f"Properties of Served Model {model_service.uuid}"

    rich_table = table.Table(
        box=box.ROUNDED,
        title=title_,
        show_lines=True,
    )
    rich_table.add_column("MODEL SERVICE PROPERTY", overflow="fold")
    rich_table.add_column("VALUE", overflow="fold")

    # Get implementation specific info
    served_model_info = model_deployer.get_model_server_info(model_service)

    served_model_info = {
        **served_model_info,
        "UUID": str(model_service.uuid),
        "STATUS": get_service_state_emoji(model_service.status.state),
        "TYPE": model_service.SERVICE_TYPE.type,
        "FLAVOR": model_service.SERVICE_TYPE.flavor,
        "STATUS_MESSAGE": model_service.status.last_error,
        "PIPELINE_NAME": model_service.config.pipeline_name,
        "PIPELINE_STEP_NAME": model_service.config.pipeline_step_name,
    }

    # Sort fields alphabetically
    sorted_items = {k: v for k, v in sorted(served_model_info.items())}

    for item in sorted_items.items():
        rich_table.add_row(*[str(elem) for elem in item])

    rich_table.columns[0]._cells = [
        component.upper()  # type: ignore[union-attr]
        for component in rich_table.columns[0]._cells
    ]
    console.print(rich_table)


def describe_pydantic_object(schema_json: Dict[str, Any]) -> None:
    """Describes a Pydantic object based on the dict-representation of its schema.

    Args:
        schema_json: str, represents the schema of a Pydantic object, which
            can be obtained through BaseModelClass.schema_json()
    """
    schema_title = schema_json["title"]
    required = schema_json.get("required", [])
    description = schema_json.get("description", "")
    properties = schema_json.get("properties", {})

    warning(f"Configuration class: {schema_title}\n", bold=True)

    if description:
        declare(f"{description}\n")

    if properties:
        warning("Properties", bold=True)
        for prop, prop_schema in properties.items():
            if "$ref" not in prop_schema.keys():
                if "type" in prop_schema.keys():
                    prop_type = prop_schema["type"]
                elif "anyOf" in prop_schema.keys():
                    prop_type = ", ".join(
                        [p.get("type", "object") for p in prop_schema["anyOf"]]
                    )
                    prop_type = f"one of: {prop_type}"
                else:
                    prop_type = "object"
                warning(
                    f"{prop}, {prop_type}"
                    f"{', REQUIRED' if prop in required else ''}"
                )

            if "description" in prop_schema:
                declare(f"  {prop_schema['description']}", width=80)


def get_boolean_emoji(value: bool) -> str:
    """Returns the emoji for displaying a boolean.

    Args:
        value: The boolean value to display

    Returns:
        The emoji for the boolean
    """
    return ":white_heavy_check_mark:" if value else ":heavy_minus_sign:"


def replace_emojis(text: str) -> str:
    """Replaces emoji shortcuts with their unicode equivalent.

    Args:
        text: Text to expand.

    Returns:
        Text with expanded emojis.
    """

    def _replace_emoji(match: re.Match[str]) -> str:
        emoji_code = match.group(1)
        try:
            return str(Emoji(emoji_code))
        except NoEmoji:
            return match.group(0)

    return re.sub(r":(\w+):", _replace_emoji, text)


def print_service_connector_resource_table(
    resources: List["ServiceConnectorResourcesModel"],
    show_resources_only: bool = False,
) -> None:
    """Prints a table with details for a list of service connector resources.

    Args:
        resources: List of service connector resources to print.
        show_resources_only: If True, only the resources will be printed.
    """

    def _truncate_error(error_msg: str, max_length: int = 100) -> str:
        """Truncate long error messages for better readability.

        Args:
            error_msg: The error message to truncate.
            max_length: The maximum length of the error message.

        Returns:
            The truncated error message.
        """
        if len(error_msg) <= max_length:
            return error_msg
        truncated = error_msg[:max_length].rsplit(" ", 1)[0]
        return f"{truncated}... (use --verbose for full error)"

    resource_table = []
    errors_found = False

    for i, resource_model in enumerate(resources):
        printed_connector = False
        resource_row: Dict[str, Any] = {}

        if resource_model.error:
            # Global error
            errors_found = True
            if not show_resources_only:
                resource_row = {
                    "CONNECTOR ID": str(resource_model.id),
                    "CONNECTOR NAME": resource_model.name,
                    "CONNECTOR TYPE": resource_model.emojified_connector_type,
                }
            resource_row.update(
                {
                    "RESOURCE TYPE": "\n".join(
                        resource_model.get_emojified_resource_types()
                    ),
                    "RESOURCE NAMES": f":collision: {_truncate_error(resource_model.error)}",
                }
            )
            resource_table.append(resource_row)
            if i < len(resources) - 1:
                if not show_resources_only:
                    resource_table.append(
                        {
                            "CONNECTOR ID": "",
                            "CONNECTOR NAME": "",
                            "CONNECTOR TYPE": "",
                            "RESOURCE TYPE": "",
                            "RESOURCE NAMES": "",
                        }
                    )
                else:
                    resource_table.append(
                        {
                            "RESOURCE TYPE": "",
                            "RESOURCE NAMES": "",
                        }
                    )
            continue

        for resource in resource_model.resources:
            resource_type = resource_model.get_emojified_resource_types(
                resource.resource_type
            )[0]
            if resource.error:
                errors_found = True
                resource_ids = [
                    f":collision: {_truncate_error(resource.error)}"
                ]
            elif resource.resource_ids:
                resource_ids = resource.resource_ids
            else:
                resource_ids = [":person_shrugging: none listed"]

            resource_row = {}
            if not show_resources_only:
                resource_row = {
                    "CONNECTOR ID": (
                        str(resource_model.id) if not printed_connector else ""
                    ),
                    "CONNECTOR NAME": (
                        resource_model.name if not printed_connector else ""
                    ),
                    "CONNECTOR TYPE": (
                        resource_model.emojified_connector_type
                        if not printed_connector
                        else ""
                    ),
                }
            resource_row.update(
                {
                    "RESOURCE TYPE": resource_type,
                    "RESOURCE NAMES": "\n".join(resource_ids),
                }
            )
            resource_table.append(resource_row)
            printed_connector = True
        if i < len(resources) - 1 and resource_model.resources:
            if not show_resources_only:
                resource_table.append(
                    {
                        "CONNECTOR ID": "",
                        "CONNECTOR NAME": "",
                        "CONNECTOR TYPE": "",
                        "RESOURCE TYPE": "",
                        "RESOURCE NAMES": "",
                    }
                )
            else:
                resource_table.append(
                    {
                        "RESOURCE TYPE": "",
                        "RESOURCE NAMES": "",
                    }
                )
    print_table(resource_table)
    if errors_found:
        console.print(
            "\n[dim]💡 Tip: Some error messages were truncated for readability. "
            "Use describe commands for full error details.[/dim]"
        )


def print_service_connector_configuration(
    connector: Union["ServiceConnectorResponse", "ServiceConnectorRequest"],
    active_status: bool,
    show_secrets: bool,
) -> None:
    """Prints the configuration options of a service connector.

    Args:
        connector: The service connector to print.
        active_status: Whether the connector is active.
        show_secrets: Whether to show secrets.
    """
    from zenml.models import ServiceConnectorResponse

    user_name = _get_user_name(connector.user)

    if isinstance(connector, ServiceConnectorResponse):
        declare(
            f"Service connector '{connector.name}' of type "
            f"'{connector.type}' with id '{connector.id}' is owned by "
            f"user '{user_name}'."
        )
    else:
        declare(
            f"Service connector '{connector.name}' of type '{connector.type}'."
        )

    title_ = f"'{connector.name}' {connector.type} Service Connector Details"

    if active_status:
        title_ += " (ACTIVE)"
    rich_table = table.Table(
        box=box.ROUNDED,
        title=title_,
        show_lines=True,
    )
    rich_table.add_column("PROPERTY")
    rich_table.add_column("VALUE", overflow="fold")

    if connector.expiration_seconds is None:
        expiration = "N/A"
    else:
        expiration = str(connector.expiration_seconds) + "s"

    if isinstance(connector, ServiceConnectorResponse):
        properties = {
            "ID": connector.id,
            "NAME": connector.name,
            "TYPE": connector.emojified_connector_type,
            "AUTH METHOD": connector.auth_method,
            "RESOURCE TYPES": ", ".join(connector.emojified_resource_types),
            "RESOURCE NAME": connector.resource_id or "<multiple>",
            "SESSION DURATION": expiration,
            "EXPIRES IN": (
                expires_in(
                    connector.expires_at,
                    ":name_badge: Expired!",
                    connector.expires_skew_tolerance,
                )
                if connector.expires_at
                else "N/A"
            ),
            "EXPIRES_SKEW_TOLERANCE": (
                connector.expires_skew_tolerance
                if connector.expires_skew_tolerance
                else "N/A"
            ),
            "OWNER": user_name,
            "CREATED_AT": connector.created,
            "UPDATED_AT": connector.updated,
        }
    else:
        properties = {
            "NAME": connector.name,
            "TYPE": connector.emojified_connector_type,
            "AUTH METHOD": connector.auth_method,
            "RESOURCE TYPES": ", ".join(connector.emojified_resource_types),
            "RESOURCE NAME": connector.resource_id or "<multiple>",
            "SESSION DURATION": expiration,
            "EXPIRES IN": (
                expires_in(
                    connector.expires_at,
                    ":name_badge: Expired!",
                    connector.expires_skew_tolerance,
                )
                if connector.expires_at
                else "N/A"
            ),
            "EXPIRES_SKEW_TOLERANCE": (
                connector.expires_skew_tolerance
                if connector.expires_skew_tolerance
                else "N/A"
            ),
        }

    for item in properties.items():
        elements = [str(elem) for elem in item]
        rich_table.add_row(*elements)

    console.print(rich_table)

    if len(connector.configuration) == 0:
        declare("No configuration options are set for this connector.")

    else:
        rich_table = table.Table(
            box=box.ROUNDED,
            title="Configuration",
            show_lines=True,
        )
        rich_table.add_column("PROPERTY")
        rich_table.add_column("VALUE", overflow="fold")

        config = connector.configuration.non_secrets
        secrets = connector.configuration.secrets
        for key, value in secrets.items():
            if not show_secrets:
                config[key] = "[HIDDEN]"
            elif value is None:
                config[key] = "[UNAVAILABLE]"
            else:
                config[key] = value.get_secret_value()

        for item in config.items():
            elements = [str(elem) for elem in item]
            rich_table.add_row(*elements)

        console.print(rich_table)

    if not connector.labels:
        declare("No labels are set for this service connector.")
        return

    rich_table = table.Table(
        box=box.ROUNDED,
        title="Labels",
        show_lines=True,
    )
    rich_table.add_column("LABEL")
    rich_table.add_column("VALUE", overflow="fold")

    items = connector.labels.items()
    for item in items:
        elements = [str(elem) for elem in item]
        rich_table.add_row(*elements)

    console.print(rich_table)


def print_service_connector_types_table(
    connector_types: Sequence["ServiceConnectorTypeModel"],
) -> None:
    """Prints a table with details for a list of service connectors types.

    Args:
        connector_types: List of service connector types to print.
    """
    if len(connector_types) == 0:
        warning("No service connector types found.")
        return

    configurations = []
    for connector_type in connector_types:
        supported_auth_methods = list(connector_type.auth_method_dict.keys())

        connector_type_config = {
            "NAME": connector_type.name,
            "TYPE": connector_type.emojified_connector_type,
            "RESOURCE TYPES": "\n".join(
                connector_type.emojified_resource_types
            ),
            "AUTH METHODS": "\n".join(supported_auth_methods),
            "LOCAL": get_boolean_emoji(connector_type.local),
            "REMOTE": get_boolean_emoji(connector_type.remote),
        }
        configurations.append(connector_type_config)
    print_table(configurations)


def print_service_connector_resource_type(
    resource_type: "ResourceTypeModel",
    title: str = "",
    heading: str = "#",
    footer: str = "---",
    print: bool = True,
) -> str:
    """Prints details for a service connector resource type.

    Args:
        resource_type: Service connector resource type to print.
        title: Markdown title to use for the resource type details.
        heading: Markdown heading to use for the resource type title.
        footer: Markdown footer to use for the resource type description.
        print: Whether to print the resource type details to the console or
            just return the message as a string.

    Returns:
        The MarkDown resource type details as a string.
    """
    message = f"{title}\n" if title else ""
    emoji = replace_emojis(resource_type.emoji) if resource_type.emoji else ""
    supported_auth_methods = [
        f"{Emoji('lock')} {a}" for a in resource_type.auth_methods
    ]
    message += (
        f"{heading} {emoji} {resource_type.name} "
        f"(resource type: {resource_type.resource_type})\n"
    )
    message += (
        f"**Authentication methods**: "
        f"{', '.join(resource_type.auth_methods)}\n\n"
    )
    message += (
        f"**Supports resource instances**: "
        f"{resource_type.supports_instances}\n\n"
    )
    message += (
        "**Authentication methods**:\n\n- "
        + "\n- ".join(supported_auth_methods)
        + "\n\n"
    )
    message += f"{resource_type.description}\n"

    message += footer

    if print:
        console.print(Markdown(message), justify="left", width=80)

    return message


def print_service_connector_auth_method(
    auth_method: "AuthenticationMethodModel",
    title: str = "",
    heading: str = "#",
    footer: str = "---",
    print: bool = True,
) -> str:
    """Prints details for a service connector authentication method.

    Args:
        auth_method: Service connector authentication method to print.
        title: Markdown title to use for the authentication method details.
        heading: Markdown heading to use for the authentication method title.
        footer: Markdown footer to use for the authentication method description.
        print: Whether to print the authentication method details to the console
            or just return the message as a string.

    Returns:
        The MarkDown authentication method details as a string.
    """
    message = f"{title}\n" if title else ""
    emoji = Emoji("lock")
    message += (
        f"{heading} {emoji} {auth_method.name} "
        f"(auth method: {auth_method.auth_method})\n"
    )
    message += (
        f"**Supports issuing temporary credentials**: "
        f"{auth_method.supports_temporary_credentials()}\n\n"
    )
    message += f"{auth_method.description}\n"

    attributes: List[str] = []
    for attr_name, attr_schema in auth_method.config_schema.get(
        "properties", {}
    ).items():
        title = attr_schema.get("title", "<no description>")
        attr_type = attr_schema.get("type", "string")
        required = attr_name in auth_method.config_schema.get("required", [])
        hidden = attr_schema.get("format", "") == "password"
        subtitles: List[str] = []
        subtitles.append(attr_type)
        if hidden:
            subtitles.append("secret")
        if required:
            subtitles.append("required")
        else:
            subtitles.append("optional")

        description = f"- `{attr_name}`"
        if subtitles:
            description = f"{description} {{{', '.join(subtitles)}}}"
        description = f"{description}: _{title}_"
        attributes.append(description)
    if attributes:
        message += "\n**Attributes**:\n"
        message += "\n".join(attributes) + "\n"

    message += footer

    if print:
        console.print(Markdown(message), justify="left", width=80)

    return message


def print_service_connector_type(
    connector_type: "ServiceConnectorTypeModel",
    title: str = "",
    heading: str = "#",
    footer: str = "---",
    include_resource_types: bool = True,
    include_auth_methods: bool = True,
    print: bool = True,
) -> str:
    """Prints details for a service connector type.

    Args:
        connector_type: Service connector type to print.
        title: Markdown title to use for the service connector type details.
        heading: Markdown heading to use for the service connector type title.
        footer: Markdown footer to use for the service connector type
            description.
        include_resource_types: Whether to include the resource types for the
            service connector type.
        include_auth_methods: Whether to include the authentication methods for
            the service connector type.
        print: Whether to print the service connector type details to the
            console or just return the message as a string.

    Returns:
        The MarkDown service connector type details as a string.
    """
    message = f"{title}\n" if title else ""
    supported_auth_methods = [
        f"{Emoji('lock')} {a.auth_method}" for a in connector_type.auth_methods
    ]
    supported_resource_types = [
        f"{replace_emojis(r.emoji)} {r.resource_type}"
        if r.emoji
        else r.resource_type
        for r in connector_type.resource_types
    ]

    emoji = (
        replace_emojis(connector_type.emoji) if connector_type.emoji else ""
    )

    message += (
        f"{heading} {emoji} {connector_type.name} "
        f"(connector type: {connector_type.connector_type})\n"
    )
    message += (
        "**Authentication methods**:\n\n- "
        + "\n- ".join(supported_auth_methods)
        + "\n\n"
    )
    message += (
        "**Resource types**:\n\n- "
        + "\n- ".join(supported_resource_types)
        + "\n\n"
    )
    message += (
        f"**Supports auto-configuration**: "
        f"{connector_type.supports_auto_configuration}\n\n"
    )
    message += f"**Available locally**: {connector_type.local}\n\n"
    message += f"**Available remotely**: {connector_type.remote}\n\n"
    message += f"{connector_type.description}\n"

    if include_resource_types:
        for r in connector_type.resource_types:
            message += print_service_connector_resource_type(
                r,
                heading=heading + "#",
                footer="",
                print=False,
            )

    if include_auth_methods:
        for a in connector_type.auth_methods:
            message += print_service_connector_auth_method(
                a,
                heading=heading + "#",
                footer="",
                print=False,
            )

    message += footer

    if print:
        console.print(Markdown(message), justify="left", width=80)

    return message


def _scrub_secret(config: StackComponentConfig) -> Dict[str, Any]:
    """Remove secret values from a configuration.

    Args:
        config: configuration for a stack component

    Returns:
        A configuration with secret values removed.
    """
    config_dict = {}
    config_fields = type(config).model_fields
    for key, value in config_fields.items():
        if getattr(config, key):
            if secret_utils.is_secret_field(value):
                config_dict[key] = "********"
            else:
                config_dict[key] = getattr(config, key)
    return config_dict


def print_debug_stack() -> None:
    """Print active stack and components for debugging purposes."""
    from zenml.client import Client

    client = Client()
    stack = client.get_stack()

    declare("\nCURRENT STACK\n", bold=True)
    console.print(f"Name: {stack.name}")
    console.print(f"ID: {str(stack.id)}")
    if stack.user and stack.user.name and stack.user.id:  # mypy check
        console.print(f"User: {stack.user.name} / {str(stack.user.id)}")

    for component_type, components in stack.components.items():
        component = components[0]
        component_response = client.get_stack_component(
            name_id_or_prefix=component.id, component_type=component.type
        )
        declare(
            f"\n{component.type.value.upper()}: {component.name}\n", bold=True
        )
        console.print(f"Name: {component.name}")
        console.print(f"ID: {str(component.id)}")
        console.print(f"Type: {component.type.value}")
        console.print(f"Flavor: {component.flavor_name}")

        flavor = Flavor.from_model(component.flavor)
        config = flavor.config_class(**component.configuration)

        console.print(f"Configuration: {_scrub_secret(config)}")
        if (
            component_response.user
            and component_response.user.name
            and component_response.user.id
        ):  # mypy check
            console.print(
                f"User: {component_response.user.name} / {str(component_response.user.id)}"
            )


def _component_display_name(
    component_type: "StackComponentType", plural: bool = False
) -> str:
    """Human-readable name for a stack component.

    Args:
        component_type: Type of the component to get the display name for.
        plural: Whether the display name should be plural or not.

    Returns:
        A human-readable name for the given stack component type.
    """
    name = component_type.plural if plural else component_type.value
    return name.replace("_", " ")


def _active_status(
    is_active: bool, output_format: OutputFormat
) -> Union[str, bool]:
    """Format active status based on output format.

    Args:
        is_active: Whether the item is active.
        output_format: The output format.

    Returns:
        For table format: green dot if active, empty string if not.
        For other formats: boolean value.
    """
    if output_format == "table":
        return "[green]●[/green]" if is_active else ""
    return is_active


def get_execution_status_emoji(status: "ExecutionStatus") -> str:
    """Returns an emoji representing the given execution status.

    Args:
        status: The execution status to get the emoji for.

    Returns:
        An emoji representing the given execution status.

    Raises:
        RuntimeError: If the given execution status is not supported.
    """
    from zenml.enums import ExecutionStatus

    if status in {ExecutionStatus.INITIALIZING, ExecutionStatus.PROVISIONING}:
        return ":hourglass_flowing_sand:"
    if status == ExecutionStatus.FAILED:
        return ":x:"
    if status == ExecutionStatus.RUNNING:
        return ":gear:"
    if status == ExecutionStatus.COMPLETED:
        return ":white_check_mark:"
    if status == ExecutionStatus.CACHED:
        return ":package:"
    if status == ExecutionStatus.STOPPED or status == ExecutionStatus.STOPPING:
        return ":stop_sign:"
    raise RuntimeError(f"Unknown status: {status}")


def fetch_snapshot(
    snapshot_name_or_id: str,
    pipeline_name_or_id: Optional[str] = None,
) -> "PipelineSnapshotResponse":
    """Fetch a snapshot by name or ID.

    Args:
        snapshot_name_or_id: The name or ID of the snapshot.
        pipeline_name_or_id: The name or ID of the pipeline.

    Returns:
        The snapshot.
    """
    if is_valid_uuid(snapshot_name_or_id):
        return Client().get_snapshot(snapshot_name_or_id)
    elif pipeline_name_or_id:
        try:
            return Client().get_snapshot(
                snapshot_name_or_id,
                pipeline_name_or_id=pipeline_name_or_id,
            )
        except KeyError:
            error(
                f"There are no snapshots with name `{snapshot_name_or_id}` for "
                f"pipeline `{pipeline_name_or_id}`."
            )
    else:
        snapshots = Client().list_snapshots(
            name=snapshot_name_or_id,
        )
        if snapshots.total == 0:
            error(f"There are no snapshots with name `{snapshot_name_or_id}`.")
        elif snapshots.total == 1:
            return snapshots.items[0]

        snapshot_index = multi_choice_prompt(
            object_type="snapshots",
            choices=[
                [snapshot.pipeline.name, snapshot.name]
                for snapshot in snapshots.items
            ],
            headers=["Pipeline", "Snapshot"],
            prompt_text=f"There are multiple snapshots with name "
            f"`{snapshot_name_or_id}`. Please select the snapshot to run",
        )
        assert snapshot_index is not None
        return snapshots.items[snapshot_index]


def get_deployment_status_emoji(
    status: Optional[str],
) -> str:
    """Returns an emoji representing the given deployment status.

    Args:
        status: The deployment status to get the emoji for.

    Returns:
        An emoji representing the given deployment status.
    """
    if status == DeploymentStatus.PENDING:
        return ":hourglass_flowing_sand:"
    if status == DeploymentStatus.ERROR:
        return ":x:"
    if status == DeploymentStatus.RUNNING:
        return ":green_circle:"
    if status == DeploymentStatus.ABSENT:
        return ":stop_sign:"

    return ":question:"


def _get_extra_columns_for_filter(filter_name: str) -> List[str]:
    """Get extra columns added by row formatter functions.

    These columns are added by generate_*_row functions and aren't part
    of the Response model itself.

    Args:
        filter_name: Name of the filter class (e.g., "StackFilter").

    Returns:
        List of extra column names added by the row formatter.
    """
    extra_columns_map: Dict[str, List[str]] = {
        "StackFilter": [ct.value.lower() for ct in StackComponentType],
        "ComponentFilter": ["flavor", "owner"],
        "DeploymentFilter": [
            "pipeline",
            "snapshot",
            "url",
            "status",
            "stack",
            "owner",
        ],
        "PipelineRunFilter": [
            "pipeline",
            "run_name",
            "status",
            "stack",
            "owner",
        ],
        "ServiceConnectorFilter": [
            "connector_type",
            "resource_types",
            "auth_method",
        ],
    }
    return extra_columns_map.get(filter_name, [])


def generate_deployment_row(
    deployment: "DeploymentResponse", output_format: OutputFormat
) -> Dict[str, Any]:
    """Generate additional data for deployment display.

    Args:
        deployment: The deployment response.
        output_format: The output format.

    Returns:
        The additional data for the deployment.
    """
    user_name = _get_user_name(deployment.user)

    if deployment.snapshot is None or deployment.snapshot.pipeline is None:
        pipeline_name = "unlisted"
    else:
        pipeline_name = deployment.snapshot.pipeline.name

    if deployment.snapshot is None or deployment.snapshot.stack is None:
        stack_name = "[DELETED]"
    else:
        stack_name = deployment.snapshot.stack.name

    status = deployment.status or DeploymentStatus.UNKNOWN.value

    if output_format == "table":
        status_emoji = get_deployment_status_emoji(status)
        status_display = f"{status_emoji} {status.upper()}"
    else:
        status_display = status.upper()

    return {
        "pipeline": pipeline_name,
        "snapshot": deployment.snapshot.name or ""
        if deployment.snapshot
        else "N/A",
        "url": deployment.url or "N/A",
        "status": status_display,
        "stack": stack_name,
        "owner": user_name,
    }


def generate_stack_row(
    stack: "StackResponse",
    output_format: OutputFormat,
    active_id: Optional["UUID"] = None,
) -> Dict[str, Any]:
    """Generate row data for stack display.

    Args:
        stack: The stack response.
        output_format: The output format.
        active_id: ID of the active stack for highlighting.

    Returns:
        Dict with stack data for display.
    """
    is_active = active_id is not None and stack.id == active_id

    row: Dict[str, Any] = {
        "active": _active_status(is_active, output_format),
    }

    for component_type in StackComponentType:
        components = stack.components.get(component_type)
        if output_format == "table":
            header = component_type.value.upper().replace("_", " ")
        else:
            header = component_type.value
        row[header] = components[0].name if components else "-"

    return row


def generate_project_row(
    project: "ProjectResponse",
    output_format: OutputFormat,
    active_id: Optional["UUID"] = None,
) -> Dict[str, Any]:
    """Generate row data for project display.

    Args:
        project: The project response.
        output_format: The output format.
        active_id: ID of the active project for highlighting.

    Returns:
        Dict with project data for display.
    """
    is_active = active_id is not None and project.id == active_id

    return {
        "active": _active_status(is_active, output_format),
    }


def generate_user_row(
    user: "UserResponse",
    output_format: OutputFormat,
    active_id: Optional["UUID"] = None,
) -> Dict[str, Any]:
    """Generate row data for user display.

    Args:
        user: The user response.
        output_format: The output format.
        active_id: ID of the active user for highlighting.

    Returns:
        Dict with user data for display.
    """
    is_active = active_id is not None and user.id == active_id

    return {
        "active": _active_status(is_active, output_format),
    }


def generate_pipeline_run_row(
    pipeline_run: "PipelineRunResponse",
    output_format: OutputFormat,
) -> Dict[str, Any]:
    """Generate row data for pipeline run display.

    Args:
        pipeline_run: The pipeline run response.
        output_format: The output format.

    Returns:
        Dict with pipeline run data for display.
    """
    pipeline_name = (
        pipeline_run.pipeline.name if pipeline_run.pipeline else "unlisted"
    )
    stack_name = pipeline_run.stack.name if pipeline_run.stack else "[DELETED]"
    user_name = _get_user_name(pipeline_run.user)
    status = pipeline_run.status
    status_emoji = get_execution_status_emoji(status)

    return {
        "pipeline": pipeline_name,
        "run_name": pipeline_run.name,
        "status": status_emoji if output_format == "table" else str(status),
        "stack": stack_name,
        "owner": user_name,
    }


def generate_component_row(
    component: "ComponentResponse",
    output_format: OutputFormat,
    active_id: Optional["UUID"] = None,
) -> Dict[str, Any]:
    """Generate row data for component display.

    Args:
        component: The component response.
        output_format: The output format.
        active_id: ID of the active component for highlighting.

    Returns:
        Dict with component data for display.
    """
    is_active = active_id is not None and component.id == active_id

    return {
        "active": _active_status(is_active, output_format),
        "name": component.name,
        "component_id": component.id,
        "flavor": component.flavor_name,
        "owner": _get_user_name(component.user),
    }


def generate_connector_row(
    connector: "ServiceConnectorResponse",
    output_format: OutputFormat,
    active_connector_ids: Optional[List["UUID"]] = None,
) -> Dict[str, Any]:
    """Generate row data for service connector display.

    Args:
        connector: The service connector response.
        output_format: The output format.
        active_connector_ids: List of active connector IDs for highlighting.

    Returns:
        Dict with connector data for display.
    """
    is_active = bool(
        active_connector_ids and connector.id in active_connector_ids
    )
    labels = [f"{label}:{value}" for label, value in connector.labels.items()]
    resource_name = connector.resource_id or "<multiple>"
    resource_types_str = "\n".join(connector.emojified_resource_types)

    return {
        "active": _active_status(is_active, output_format),
        "name": connector.name,
        "id": connector.id,
        "type": connector.emojified_connector_type,
        "resource_types": resource_types_str,
        "resource_name": resource_name,
        "owner": _get_user_name(connector.user),
        "expires_in": (
            expires_in(
                connector.expires_at,
                ":name_badge: Expired!",
                connector.expires_skew_tolerance,
            )
            if connector.expires_at
            else ""
        ),
        "labels": "\n".join(labels),
    }


def pretty_print_deployment(
    deployment: "DeploymentResponse",
    show_secret: bool = False,
    show_metadata: bool = False,
    show_schema: bool = False,
    no_truncate: bool = False,
) -> None:
    """Print a prettified deployment with organized sections.

    Args:
        deployment: The deployment to print.
        show_secret: Whether to show the auth key or mask it.
        show_metadata: Whether to show the metadata.
        show_schema: Whether to show the schema.
        no_truncate: Whether to truncate the metadata.
    """
    # Header section
    status_label = (deployment.status or "UNKNOWN").upper()
    status_emoji = get_deployment_status_emoji(deployment.status)
    declare(
        f"\n[bold]Deployment:[/bold] [bold cyan]{deployment.name}[/bold cyan] status: {status_label} {status_emoji}"
    )
    if deployment.snapshot is None:
        pipeline_name = "N/A"
        snapshot_name = "N/A"
    else:
        pipeline_name = deployment.snapshot.pipeline.name
        snapshot_name = deployment.snapshot.name or str(deployment.snapshot.id)
    if deployment.snapshot is None or deployment.snapshot.stack is None:
        stack_name = "[DELETED]"
    else:
        stack_name = deployment.snapshot.stack.name
    declare(f"\n[bold]Pipeline:[/bold] [bold cyan]{pipeline_name}[/bold cyan]")
    declare(f"[bold]Snapshot:[/bold] [bold cyan]{snapshot_name}[/bold cyan]")
    declare(f"[bold]Stack:[/bold] [bold cyan]{stack_name}[/bold cyan]")

    # Connection section
    if deployment.url:
        declare("\n[bold]Connection information:[/bold]")

        declare(
            f"\n[bold]Endpoint URL:[/bold] [link]{deployment.url}[/link]",
            no_wrap=True,
        )
        declare(
            f"[bold]Swagger URL:[/bold] [link]{deployment.url.rstrip('/')}/docs[/link]",
            no_wrap=True,
        )

        # Auth key handling with proper security
        auth_key = deployment.auth_key
        if auth_key:
            if show_secret:
                declare(f"[bold]Auth key:[/bold] [yellow]{auth_key}[/yellow]")
            else:
                masked_key = (
                    f"{auth_key[:8]}***" if len(auth_key) > 8 else "***"
                )
                declare(
                    f"[bold]Auth key:[/bold] [yellow]{masked_key}[/yellow] "
                    f"[dim](run `zenml deployment describe {deployment.name} --show-secret` to reveal)[/dim]"
                )

        example = get_deployment_invocation_example(deployment)

        # CLI invoke command
        cli_args = " ".join(
            [
                f"--{k}="
                + (
                    f"'{json.dumps(v)}'"
                    if isinstance(v, (dict, list))
                    else json.dumps(v)
                )
                for k, v in example.items()
            ]
        )
        cli_command = f"zenml deployment invoke {deployment.name} {cli_args}"

        declare("[bold]CLI command example:[/bold]")
        console.print(cli_command)

        # cURL example
        declare("\n[bold]cURL example:[/bold]")
        curl_headers = []
        if auth_key:
            if show_secret:
                curl_headers.append(f'-H "Authorization: Bearer {auth_key}"')
            else:
                curl_headers.append(
                    '-H "Authorization: Bearer <YOUR_AUTH_KEY>"'
                )

        curl_params = json.dumps(example, indent=2).replace("\n", "\n    ")

        curl_headers.append('-H "Content-Type: application/json"')
        headers_str = "\\\n  ".join(curl_headers)

        curl_command = f"""curl -X POST {deployment.url}/invoke \\
  {headers_str} \\
  -d '{{
    "parameters": {curl_params}
  }}'"""

        console.print(curl_command)

    # JSON Schemas
    if show_schema:
        input_schema = get_deployment_input_schema(deployment)
        output_schema = get_deployment_output_schema(deployment)
        declare("\n[bold]Deployment JSON schemas:[/bold]")
        declare("\n[bold]Input schema:[/bold]")
        schema_json = json.dumps(input_schema, indent=2)
        console.print(schema_json)
        declare("\n[bold]Output schema:[/bold]")
        schema_json = json.dumps(output_schema, indent=2)
        console.print(schema_json)

    # Metadata section
    if show_metadata:
        declare("\n[bold]Deployment metadata:[/bold]")

        # Get the metadata - it could be from deployment_metadata property or metadata
        metadata = deployment.deployment_metadata

        if metadata:
            # Recursively format nested dictionaries and lists
            def format_value(value: Any, indent_level: int = 0) -> str:
                if isinstance(value, dict):
                    if not value:
                        return "[dim]{}[/dim]"
                    formatted_items: List[str] = []
                    for k, v in value.items():
                        formatted_v = format_value(v, indent_level + 1)
                        formatted_items.append(
                            f"  {'  ' * indent_level}[bold]{k}[/bold]: {formatted_v}"
                        )
                    return "\n" + "\n".join(formatted_items)
                elif isinstance(value, list):
                    if not value:
                        return "[dim][][/dim]"
                    formatted_items = []
                    for i, item in enumerate(value):
                        formatted_item = format_value(item, indent_level + 1)
                        formatted_items.append(
                            f"  {'  ' * indent_level}[{i}]: {formatted_item}"
                        )
                    return "\n" + "\n".join(formatted_items)
                elif isinstance(value, str):
                    # Handle long strings by truncating if needed
                    if len(value) > 100 and not no_truncate:
                        return f"[green]{value[:97]}...[/green]"
                    return f"[green]{value}[/green]"
                elif isinstance(value, bool):
                    return f"[yellow]{value}[/yellow]"
                elif isinstance(value, (int, float)):
                    return f"[blue]{value}[/blue]"
                elif value is None:
                    return "[dim]null[/dim]"
                else:
                    return f"[white]{str(value)}[/white]"

            formatted_metadata = format_value(metadata)
            console.print(formatted_metadata)
        else:
            declare("  [dim]No metadata available[/dim]")

    # Management section
    declare("\n[bold]Management commands[/bold]\n")

    console.print(f"[bold]zenml deployment logs {deployment.name} -f[/bold]")
    console.print("  [dim]Follow deployment logs in real time[/dim]\n")

    console.print(f"[bold]zenml deployment describe {deployment.name}[/bold]")
    console.print("  [dim]Show detailed deployment information[/dim]\n")

    console.print(
        f"[bold]zenml deployment deprovision {deployment.name}[/bold]"
    )
    console.print(
        "  [dim]Deprovision this deployment and keep a record of it[/dim]\n"
    )

    console.print(f"[bold]zenml deployment delete {deployment.name}[/bold]")
    console.print("  [dim]Deprovision and delete this deployment[/dim]")


def check_zenml_pro_project_availability() -> None:
    """Check if the ZenML Pro project feature is available."""
    client = Client()
    if not client.zen_store.get_store_info().is_pro_server():
        warning(
            "The ZenML projects feature is available only on ZenML Pro. "
            "Please visit https://zenml.io/pro to learn more."
        )


def print_page_info(page: "Page[Any]") -> None:
    """Print all page information showing the number of items and pages.

    Args:
        page: The page object containing pagination information.
    """
    declare(
        f"Page `({page.index}/{page.total_pages})`, "
        f"`{page.total}` items found for the applied filters."
    )


F = TypeVar("F", bound=Callable[..., None])


def create_filter_help_text(filter_model: Type[BaseFilter], field: str) -> str:
    """Create the help text used in the click option help text.

    Args:
        filter_model: The filter model to use
        field: The field within that filter model

    Returns:
        The help text.
    """
    filter_generator = FilterGenerator(filter_model)
    if filter_generator.is_sort_by_field(field):
        return (
            "[STRING] Example: --sort_by='desc:name' to sort by name in "
            "descending order. "
        )
    if filter_generator.is_datetime_field(field):
        return (
            f"[DATETIME] The following datetime format is supported: "
            f"'{FILTERING_DATETIME_FORMAT}'. Make sure to keep it in "
            f"quotation marks. "
            f"Example: --{field}="
            f"'{GenericFilterOps.GTE}:{FILTERING_DATETIME_FORMAT}' to "
            f"filter for everything created on or after the given date."
        )
    elif filter_generator.is_uuid_field(field):
        return (
            f"[UUID] Example: --{field}='{GenericFilterOps.STARTSWITH}:ab53ca' "
            f"to filter for all UUIDs starting with that prefix."
        )
    elif filter_generator.is_int_field(field):
        return (
            f"[INTEGER] Example: --{field}='{GenericFilterOps.GTE}:25' to "
            f"filter for all entities where this field has a value greater than "
            f"or equal to the value."
        )
    elif filter_generator.is_bool_field(field):
        return (
            f"[BOOL] Example: --{field}='True' to "
            f"filter for all instances where this field is true."
        )
    elif filter_generator.is_str_field(field):
        return (
            f"[STRING] Example: --{field}='{GenericFilterOps.CONTAINS}:example' "
            f"to filter everything that contains the query string somewhere in "
            f"its {field}."
        )
    else:
        return ""


def create_data_type_help_text(
    filter_model: Type[BaseFilter], field: str
) -> str:
    """Create a general help text for a fields datatype.

    Args:
        filter_model: The filter model to use
        field: The field within that filter model

    Returns:
        The help text.
    """
    filter_generator = FilterGenerator(filter_model)
    if filter_generator.is_datetime_field(field):
        return (
            f"[DATETIME] supported filter operators: "
            f"{[str(op) for op in NumericFilter.ALLOWED_OPS]}"
        )
    elif filter_generator.is_uuid_field(field):
        return (
            f"[UUID] supported filter operators: "
            f"{[str(op) for op in UUIDFilter.ALLOWED_OPS]}"
        )
    elif filter_generator.is_int_field(field):
        return (
            f"[INTEGER] supported filter operators: "
            f"{[str(op) for op in NumericFilter.ALLOWED_OPS]}"
        )
    elif filter_generator.is_bool_field(field):
        return (
            f"[BOOL] supported filter operators: "
            f"{[str(op) for op in BoolFilter.ALLOWED_OPS]}"
        )
    elif filter_generator.is_str_field(field):
        return (
            f"[STRING] supported filter operators: "
            f"{[str(op) for op in StrFilter.ALLOWED_OPS]}"
        )
    else:
        return f"{field}"


def _is_list_field(field_info: Any) -> bool:
    """Check if a field is a list field.

    Args:
        field_info: The field info to check.

    Returns:
        True if the field is a list field, False otherwise.
    """
    field_type = field_info.annotation
    origin = get_origin(field_type)
    return origin is list or (
        is_union(origin)
        and any(get_origin(arg) is list for arg in field_type.__args__)
    )


def _get_response_columns_for_filter(
    filter_model: Type[BaseFilter],
) -> List[str]:
    """Get available column names by introspecting the Response model.

    Derives the Response model name from the Filter model name and extracts
    field names from its body, metadata, and resources classes. Also includes
    extra columns added by generate_*_row functions.

    Args:
        filter_model: The filter model class.

    Returns:
        List of available column names, or empty list if derivation fails.
    """
    from typing import get_args as typing_get_args
    from typing import get_origin as typing_get_origin

    import zenml.models as models_module

    filter_name = filter_model.__name__
    if not filter_name.endswith("Filter"):
        return []

    response_name = filter_name.replace("Filter", "Response")
    response_class = getattr(models_module, response_name, None)
    if response_class is None:
        return []

    columns: Set[str] = {"id"}

    if "name" in response_class.model_fields:
        columns.add("name")

    for attr_name in ["body", "metadata", "resources"]:
        field_info = response_class.model_fields.get(attr_name)
        if field_info is None:
            continue
        annotation = field_info.annotation
        origin = typing_get_origin(annotation)
        if origin is not None:
            args = typing_get_args(annotation)
            for arg in args:
                if arg is not type(None) and hasattr(arg, "model_fields"):
                    for field_name in arg.model_fields:
                        columns.add(field_name.lower().replace(" ", "_"))
                    break
        elif hasattr(annotation, "model_fields"):
            for field_name in annotation.model_fields:
                columns.add(field_name.lower().replace(" ", "_"))

    extra_columns = _get_extra_columns_for_filter(filter_name)
    columns.update(extra_columns)

    return sorted(columns)


def list_options(
    filter_model: Type[BaseFilter],
    default_columns: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Add filter and output options to a list command.

    This decorator generates click options from a FilterModel and adds standard
    output formatting options (--columns, --output). The decorated function
    receives these as regular parameters - no magic interception!

    The function should call print_page() to render results.

    Args:
        filter_model: The filter model to generate filter options from.
        default_columns: Optional list of column names to use as defaults.

    Returns:
        The decorator function.

    Example:
        ```python
        @list_options(StackFilter, default_columns=["id", "name"])
        def list_stacks(columns: str, output_format: str, **kwargs: Any) -> None:
            stacks = Client().list_stacks(**kwargs)
            if not stacks.items:
                declare("No stacks found")
                return
            print_page(stacks, columns, output_format)
        ```
    """

    def inner_decorator(func: F) -> F:
        options = []
        data_type_descriptors = set()
        for k, v in filter_model.model_fields.items():
            if k not in filter_model.CLI_EXCLUDE_FIELDS:
                options.append(
                    click.option(
                        f"--{k}",
                        type=str,
                        default=v.default,
                        required=False,
                        multiple=_is_list_field(v),
                        help=create_filter_help_text(filter_model, k),
                    )
                )
            if k not in filter_model.FILTER_EXCLUDE_FIELDS:
                data_type_descriptors.add(
                    create_data_type_help_text(filter_model, k)
                )

        default_columns_list = default_columns or []
        default_columns_str = ",".join(default_columns_list)

        derived_columns = _get_response_columns_for_filter(filter_model)
        all_columns = sorted(set(derived_columns) | set(default_columns_list))
        columns_help = (
            "Comma-separated list of columns to display, or 'all' "
            "for all columns."
        )
        if all_columns:
            columns_help += f" Available: {', '.join(all_columns)}."

        options.extend(
            [
                click.option(
                    "--columns",
                    "-c",
                    type=str,
                    default=default_columns_str,
                    help=columns_help,
                ),
                click.option(
                    "--output",
                    "-o",
                    "output_format",
                    type=click.Choice(["table", "json", "yaml", "tsv", "csv"]),
                    default=get_default_output_format(),
                    help="Output format for the list.",
                ),
            ]
        )

        def wrapper(function: F) -> F:
            for option in reversed(options):
                function = option(function)
            return function

        func.__doc__ = (
            f"{func.__doc__} By default all filters are "
            f"interpreted as a check for equality. However advanced "
            f"filter operators can be used to tune the filtering by "
            f"writing the operator and separating it from the "
            f"query parameter with a colon `:`, e.g. "
            f"--field='operator:query'."
        )

        if data_type_descriptors:
            joined_data_type_descriptors = "\n\n".join(data_type_descriptors)

            func.__doc__ = (
                f"{func.__doc__} \n\n"
                f"\b Each datatype supports a specific "
                f"set of filter operations, here are the relevant "
                f"ones for the parameters of this command: \n\n"
                f"{joined_data_type_descriptors}"
            )

        return wrapper(func)

    return inner_decorator


@contextlib.contextmanager
def temporary_active_stack(
    stack_name_or_id: Union["UUID", str, None] = None,
) -> Iterator["Stack"]:
    """Contextmanager to temporarily activate a stack.

    Args:
        stack_name_or_id: The name or ID of the stack to activate. If not given,
            this contextmanager will not do anything.

    Yields:
        The active stack.
    """
    from zenml.client import Client

    try:
        if stack_name_or_id:
            old_stack_id = Client().active_stack_model.id
            Client().activate_stack(stack_name_or_id)
        else:
            old_stack_id = None
        yield Client().active_stack
    finally:
        if old_stack_id:
            Client().activate_stack(old_stack_id)


def get_parsed_labels(
    labels: Optional[List[str]], allow_label_only: bool = False
) -> Dict[str, Optional[str]]:
    """Parse labels into a dictionary.

    Args:
        labels: The labels to parse.
        allow_label_only: Whether to allow labels without values.

    Returns:
        A dictionary of the metadata.

    Raises:
        ValueError: If the labels are not in the correct format.
    """
    if not labels:
        return {}

    metadata_dict = {}
    for m in labels:
        try:
            key, value = m.split("=")
        except ValueError:
            if not allow_label_only:
                raise ValueError(
                    "Labels must be in the format key=value"
                ) from None
            key = m
            value = None
        metadata_dict[key] = value

    return metadata_dict


def is_sorted_or_filtered(ctx: click.Context) -> bool:
    """Decides whether any filtering/sorting happens during a 'list' CLI call.

    Args:
        ctx: the Click context of the CLI call.

    Returns:
        True if any parameter source differs from default, else False.
    """
    display_options = {"output_format", "columns"}
    try:
        for param, source in ctx._parameter_source.items():
            if param in display_options:
                continue
            if source != click.core.ParameterSource.DEFAULT:
                return True
        return False
    except Exception as e:
        logger.debug(
            f"There was a problem accessing the parameter source for "
            f'the "sort_by" option: {e}'
        )
        return False


def print_model_url(url: Optional[str]) -> None:
    """Pretty prints a given URL on the CLI.

    Args:
        url: optional str, the URL to display.
    """
    if url:
        declare(f"Dashboard URL: {url}")
    else:
        warning(
            "You can display various ZenML entities including pipelines, "
            "runs, stacks and much more on the ZenML Dashboard. "
            "You can try it locally, by running `zenml login --local`, or "
            "remotely, by deploying ZenML on the infrastructure of your choice."
        )


def is_jupyter_installed() -> bool:
    """Checks if Jupyter notebook is installed.

    Returns:
        bool: True if Jupyter notebook is installed, False otherwise.
    """
    return requirement_installed("notebook")


def multi_choice_prompt(
    object_type: str,
    choices: List[List[Any]],
    headers: List[str],
    prompt_text: str,
    allow_zero_be_a_new_object: bool = False,
    default_choice: Optional[str] = None,
) -> Optional[int]:
    """Prompts the user to select a choice from a list of choices.

    Args:
        object_type: The type of the object
        choices: The list of choices
        prompt_text: The prompt text
        headers: The list of headers.
        allow_zero_be_a_new_object: Whether to allow zero as a new object
        default_choice: The default choice

    Returns:
        The selected choice index or None for new object

    Raises:
        RuntimeError: If no choice is made.
    """
    table = Table(
        title=f"Available {object_type}",
        show_header=True,
        expand=True,
        show_lines=False,
    )
    table.add_column("Choice", justify="left", width=1)
    for h in headers:
        table.add_column(
            h.replace("_", " ").capitalize(), justify="left", width=10
        )

    i_shift = 0
    if allow_zero_be_a_new_object:
        i_shift = 1
        table.add_row(
            "[0]",
            *([f"Create a new {object_type}"] * len(headers)),
        )
    for i, one_choice in enumerate(choices):
        table.add_row(f"[{i + i_shift}]", *[str(x) for x in one_choice])
    Console().print(table)

    selected = Prompt.ask(
        prompt_text,
        choices=[str(i) for i in range(0, len(choices) + 1)],
        default=default_choice,
        show_choices=False,
    )
    if selected is None:
        raise RuntimeError(f"No {object_type} was selected")

    if selected == "0" and allow_zero_be_a_new_object:
        return None
    return int(selected) - i_shift


def requires_mac_env_var_warning() -> bool:
    """Checks if a warning needs to be shown for a local Mac server.

    This is for the case where a user is on a macOS system, trying to run a
    local server but is missing the `OBJC_DISABLE_INITIALIZE_FORK_SAFETY`
    environment variable.

    Returns:
        bool: True if a warning needs to be shown, False otherwise.
    """
    if sys.platform == "darwin":
        mac_version_tuple = tuple(map(int, platform.release().split(".")[:2]))
        return not os.getenv(
            "OBJC_DISABLE_INITIALIZE_FORK_SAFETY"
        ) and mac_version_tuple >= (10, 13)
    return False


def get_default_output_format() -> OutputFormat:
    """Get the default output format from environment variable.

    Returns:
        The default output format, falling back to "table" if not configured
        or if the configured value is invalid.
    """
    value = os.environ.get(ENV_ZENML_DEFAULT_OUTPUT, "table")
    valid_formats = get_args(OutputFormat)
    if value in valid_formats:
        return cast(OutputFormat, value)
    return "table"


def prepare_response_data(item: AnyResponse) -> Dict[str, Any]:
    """Prepare data from BaseResponse instances.

    This function extracts data from body, metadata, and resources of a
    response model to create a flat dictionary suitable for CLI display.
    It simplifies known nested objects (tags, components, user) to their
    name representations.

    Args:
        item: BaseResponse instance to format

    Returns:
        Dictionary with the data
    """

    def _simplify_response(val: Any) -> Any:
        """Simplify a value: Response -> name/id, list -> names, else as-is.

        Args:
            val: Value to simplify

        Returns:
            Simplified value
        """
        if isinstance(val, BaseIdentifiedResponse):
            return val.name if hasattr(val, "name") else str(val.id)
        if isinstance(val, list) and val:
            if isinstance(val[0], BaseIdentifiedResponse):
                return [
                    v.name if hasattr(v, "name") else str(v.id) for v in val
                ]
        if isinstance(val, dict) and val:
            first_val = next(iter(val.values()), None)
            if isinstance(first_val, list) and first_val:
                if isinstance(first_val[0], BaseIdentifiedResponse):
                    return {
                        (k.value if hasattr(k, "value") else k): [
                            v.name if hasattr(v, "name") else str(v.id)
                            for v in vs
                        ]
                        for k, vs in val.items()
                    }
        return None

    def _process_model_fields(model: BaseModel) -> Dict[str, Any]:
        """Extract fields, simplifying nested responses to names.

        Args:
            model: Pydantic model to extract fields from

        Returns:
            Dictionary with simplified field values
        """
        result: Dict[str, Any] = {}
        for field_name in type(model).model_fields:
            val = getattr(model, field_name)
            simplified = _simplify_response(val)
            if simplified is not None:
                result[field_name] = simplified
            elif isinstance(val, BaseModel):
                result[field_name] = val.model_dump(mode="json")
            elif isinstance(val, UUID):
                result[field_name] = str(val)
            elif hasattr(val, "value"):  # Enum
                result[field_name] = val.value
            else:
                result[field_name] = val
        return result

    item_data: Dict[str, Any] = {"id": str(item.id)}

    if "name" in type(item).model_fields:
        item_data["name"] = getattr(item, "name")

    if item.body is not None:
        item_data.update(_process_model_fields(item.body))

    if item.metadata is not None:
        item_data.update(_process_model_fields(item.metadata))

    if item.resources is not None:
        item_data.update(_process_model_fields(item.resources))

    if isinstance(item, UserScopedResponse) and item.user:
        item_data["user"] = item.user.name

    return item_data


def format_page_items(
    page: Page[AnyResponse],
    row_formatter: Optional[
        Callable[[Any, OutputFormat], Dict[str, Any]]
    ] = None,
    output_format: OutputFormat = "table",
) -> List[Dict[str, Any]]:
    """Convert a Page of response models to a list of dicts for display.

    This is a lower-level helper that combines prepare_response_data with
    optional custom formatting. For most use cases, prefer print_page() which
    handles both formatting and output in a single call.

    Args:
        page: Page of response items to convert.
        row_formatter: Optional function to add custom fields to each row.
            Should accept (item, output_format) and return a dict of additional fields.
        output_format: Output format to pass to row_formatter (table/json/yaml/etc).

    Returns:
        List of dicts ready to pass to handle_output.

    Example:
        ```python
        # Prefer print_page() for simple cases:
        print_page(stacks_page, columns, output_format, generate_stack_row)

        # Use format_page_items() when you need to modify items before output:
        items = format_page_items(stacks_page, generate_stack_row, output_format)
        # ... modify items ...
        handle_output(items, stacks_page, columns, output_format)
        ```
    """
    result = []
    for item in page.items:
        item_data = prepare_response_data(item)
        if row_formatter:
            additional_data = row_formatter(item, output_format)
            if additional_data:
                item_data.update(additional_data)
        result.append(item_data)
    return result


def print_page(
    page: Page[AnyResponse],
    columns: str,
    output_format: OutputFormat,
    row_formatter: Optional[
        Callable[[Any, OutputFormat], Dict[str, Any]]
    ] = None,
    column_aliases: Optional[Dict[str, str]] = None,
    *,
    empty_message: str = "No items found for this filter.",
    row_generator: Optional[Callable[..., Dict[str, Any]]] = None,
    active_id: Optional["UUID"] = None,
) -> None:
    """Format and print a page of response items.

    This is a convenience function that combines format_page_items and
    handle_output into a single call for cleaner CLI command implementations.
    It also handles empty pages and active item highlighting automatically.

    Args:
        page: Page of response items to display.
        columns: Comma-separated column names. If empty, all columns are shown.
        output_format: Output format (table, json, yaml, tsv, csv).
        row_formatter: Optional function to add custom fields to each row.
            Should accept (item, output_format) and return a dict of additional
            fields. Use this for complex row formatting logic.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.
        empty_message: Message to display when the page has no items.
        row_generator: Optional row generator function that accepts active_id.
            When provided with active_id, creates a row_formatter automatically.
            Use this for simple active item highlighting.
        active_id: ID of the active item for highlighting. Used together with
            row_generator to create the row_formatter.
    """
    if not page.total:
        declare(empty_message)
        return

    if row_generator is not None:
        row_formatter = partial(row_generator, active_id=active_id)

    items = format_page_items(page, row_formatter, output_format)
    handle_output(items, page, columns, output_format, column_aliases)


def handle_output(
    data: List[Dict[str, Any]],
    page: Optional["Page[Any]"],
    columns: str,
    output_format: OutputFormat,
    column_aliases: Optional[Dict[str, str]] = None,
) -> None:
    """Handle output formatting for CLI commands.

    This function processes the output formatting parameters from CLI options
    and calls the appropriate rendering function.

    Args:
        data: List of dictionaries to render
        page: Page object containing pagination info
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated column names. If empty, all columns are shown.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.
    """
    cli_output = prepare_output(
        data=data,
        output_format=output_format,
        columns=columns,
        page=page,
        column_aliases=column_aliases,
    )
    if cli_output:
        from zenml_cli import clean_output

        try:
            clean_output(cli_output)
        except (IOError, OSError) as err:
            logger.warning("Failed to write clean output: %s", err)
            print(cli_output)

    if page and output_format == "table":
        print_page_info(page)


def prepare_output(
    data: List[Dict[str, Any]],
    output_format: OutputFormat = "table",
    columns: Optional[str] = None,
    page: Optional["Page[Any]"] = None,
    column_aliases: Optional[Dict[str, str]] = None,
) -> str:
    """Render data in specified format following ZenML CLI table guidelines.

    This function provides a centralized way to render tabular data across
    all ZenML CLI commands with consistent formatting and multiple output
    formats.

    Args:
        data: List of dictionaries to render.
        output_format: Output format (`table`, `json`, `yaml`, `tsv`, `csv`).
        columns: Optional comma-separated list of column names to include.
            Unrecognized column names will trigger a warning.
        page: Optional page object for pagination metadata in JSON/YAML output.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.

    Returns:
        The rendered output in the specified format, or empty string if
        no data is provided.

    Raises:
        ValueError: If an unsupported output format is provided.
    """
    if not data:
        return ""

    available_keys = list(data[0].keys())

    if columns and columns.strip().lower() == "all":
        selected_columns = available_keys
    elif columns:
        requested_cols = [c.strip() for c in columns.split(",")]
        col_mapping: Dict[str, str] = {}
        unmatched_cols: List[str] = []

        for req_col in requested_cols:
            req_normalized = req_col.lower().replace("_", " ")
            if req_col in available_keys:
                col_mapping[req_col] = req_col
            else:
                matched = False
                for key in available_keys:
                    key_normalized = key.lower().replace("_", " ")
                    if req_normalized == key_normalized:
                        col_mapping[req_col] = key
                        matched = True
                        break
                if not matched:
                    unmatched_cols.append(req_col)

        if unmatched_cols:
            normalized_keys = [
                key.lower().replace(" ", "_") for key in available_keys
            ]
            available_display = ", ".join(sorted(set(normalized_keys)))
            warning(
                f"Unknown column(s) ignored: {', '.join(unmatched_cols)}. "
                f"Available: {available_display}"
            )

        selected_columns = list(col_mapping.values())
    else:
        selected_columns = list(data[0].keys())

    filtered_data = [
        {k: entry[k] for k in selected_columns if k in entry} for entry in data
    ]

    pagination_dict = (
        {
            "index": page.index,
            "max_size": page.max_size,
            "total_pages": page.total_pages,
            "total": page.total,
        }
        if page
        else None
    )

    if output_format == "json":
        return _render_json(filtered_data, pagination=pagination_dict)
    elif output_format == "yaml":
        return _render_yaml(filtered_data, pagination=pagination_dict)
    elif output_format == "tsv":
        return _render_tsv(filtered_data)
    elif output_format == "csv":
        return _render_csv(filtered_data)
    elif output_format == "table":
        return _render_table(filtered_data, column_aliases=column_aliases)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def _syntax_highlight(content: str, lexer: str) -> str:
    """Apply syntax highlighting to content if colors are enabled.

    Syntax highlighting is only applied when output goes to an interactive
    terminal (TTY). When output is redirected to a file or piped to another
    program, plain text is returned to ensure machine-readable output.

    Args:
        content: The text content to highlight
        lexer: The lexer to use (e.g., "json", "yaml")

    Returns:
        Syntax-highlighted string if colors enabled and output is a TTY,
        otherwise the original content unchanged.
    """
    if os.getenv("NO_COLOR"):
        return content

    # Import here to avoid circular imports at module load time
    from zenml_cli import is_terminal_output

    if not is_terminal_output():
        return content

    syntax = Syntax(
        content, lexer, theme="ansi_dark", background_color="default"
    )
    output_buffer = io.StringIO()
    temp_console = Console(file=output_buffer, force_terminal=True)
    temp_console.print(syntax)
    return output_buffer.getvalue().rstrip()


def _render_json(
    data: List[Dict[str, Any]],
    pagination: Optional[Dict[str, Any]] = None,
) -> str:
    """Render data as JSON.

    Args:
        data: List of data dictionaries to render
        pagination: Optional pagination metadata

    Returns:
        JSON string representation of the data
    """
    output: Dict[str, Any] = {"items": data}

    if pagination:
        output["pagination"] = pagination

    json_str = json.dumps(output, indent=2, default=str)
    return _syntax_highlight(json_str, "json")


def _render_yaml(
    data: List[Dict[str, Any]],
    pagination: Optional[Dict[str, Any]] = None,
) -> str:
    """Render data as YAML.

    Args:
        data: List of data dictionaries to render
        pagination: Optional pagination metadata

    Returns:
        YAML string representation of the data
    """
    output: Dict[str, Any] = {"items": data}

    if pagination:
        output["pagination"] = pagination

    yaml_str = yaml.dump(output, default_flow_style=False)
    return _syntax_highlight(yaml_str, "yaml")


def _render_delimited(
    data: List[Dict[str, Any]],
    delimiter: str = ",",
) -> str:
    """Render data as delimited values (CSV/TSV).

    Args:
        data: List of data dictionaries to render
        delimiter: Field delimiter character

    Returns:
        Delimited string representation of the data
    """
    if not data:
        return ""

    output_buffer = io.StringIO()
    headers = list(data[0].keys())
    writer = csv.DictWriter(
        output_buffer,
        fieldnames=headers,
        delimiter=delimiter,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(data)
    return output_buffer.getvalue().strip()


def _render_tsv(data: List[Dict[str, Any]]) -> str:
    """Render data as TSV (Tab-Separated Values).

    Args:
        data: List of data dictionaries to render

    Returns:
        TSV string representation of the data
    """
    return _render_delimited(data, delimiter="\t")


def _render_csv(data: List[Dict[str, Any]]) -> str:
    """Render data as CSV (Comma-Separated Values).

    Args:
        data: List of data dictionaries to render

    Returns:
        CSV string representation of the data
    """
    return _render_delimited(data, delimiter=",")


def _get_terminal_width() -> Optional[int]:
    """Get terminal width from ZENML_CLI_COLUMN_WIDTH environment variable or shutil.

    Checks the ZENML_CLI_COLUMN_WIDTH environment variable first, then falls back
    to shutil.get_terminal_size() for automatic detection.

    Returns:
        Terminal width in characters, or None if cannot be determined
    """
    columns_env = handle_int_env_var(ENV_ZENML_CLI_COLUMN_WIDTH, default=0)
    if columns_env > 0:
        return columns_env

    try:
        size = shutil.get_terminal_size()
        return size.columns
    except (AttributeError, OSError):
        return None


def _render_table(
    data: List[Dict[str, Any]],
    title: Optional[str] = None,
    caption: Optional[str] = None,
    column_aliases: Optional[Dict[str, str]] = None,
) -> str:
    """Render data as a formatted table following ZenML guidelines.

    Args:
        data: List of data dictionaries to render
        title: Optional title for the table.
        caption: Optional caption for the table.
        column_aliases: Optional mapping of original column names to display
            names. Use this to rename columns in the table output.

    Returns:
        Formatted table string representation of the data
    """
    aliases = column_aliases or {}
    headers = list(data[0].keys())
    longest_values: Dict[str, int] = {}
    for header in headers:
        display_name = aliases.get(header, header)
        header_display = display_name.replace("_", " ").upper()
        longest_values[header] = max(
            len(header_display),
            max(len(str(row.get(header, ""))) for row in data),
        )

    terminal_width = _get_terminal_width()
    console_width = (
        max(80, min(terminal_width, 200)) if terminal_width else 150
    )
    estimated_width = sum(longest_values.values()) + (len(headers) * 3)

    if estimated_width > console_width:
        declare(
            "Large tables may wrap, truncate, or hide columns depending on terminal "
            "width.\n"
            "- Use --output =json|yaml|csv|tsv for full data\n"
            "- Or optionally limit visible columns with --columns\n"
        )

    rich_table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        show_lines=False,
        pad_edge=False,
        collapse_padding=False,
        expand=False,
        show_edge=False,
        header_style="bold",
        title=title,
        caption=caption,
    )

    for header in headers:
        lower = header.lower().strip()
        is_active_col = lower == "active"
        is_id_col = _is_id_column(header)
        is_name_col = _is_name_column(header)
        display_name = aliases.get(header, header)
        header_display = (
            "active"
            if is_active_col
            else display_name.replace("_", " ").upper()
        )
        justify: Literal["default", "left", "center", "right", "full"] = "left"
        overflow: Literal["fold", "crop", "ellipsis", "ignore"] = "ellipsis"
        min_width: Optional[int] = None
        no_wrap = False

        if is_active_col:
            justify = "center"
            overflow = "crop"
            no_wrap = True
        elif is_id_col or is_name_col:
            overflow = "fold"
            min_width = longest_values[header]

        rich_table.add_column(
            header=header_display,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            min_width=min_width,
        )

    if data:
        rich_table.add_section()

    for row in data:
        values = []
        for header in headers:
            value = str(row.get(header, ""))

            if not os.getenv("NO_COLOR"):
                value = _colorize_value(header, value)
                if value.startswith("http") and " " not in value:
                    value = f"[link={value}]{value}[/link]"

            values.append(value)

        rich_table.add_row(*values)

    output_buffer = io.StringIO()
    table_console = Console(
        width=console_width,
        force_terminal=not os.getenv("NO_COLOR"),
        no_color=os.getenv("NO_COLOR") is not None,
        file=output_buffer,
    )
    padded_table = Padding(rich_table, (0, 0, 1, 2))
    table_console.print(padded_table)

    return output_buffer.getvalue()


def _colorize_value(column: str, value: str) -> str:
    """Apply colorization to values based on column type and content.

    Args:
        column: Column name to determine colorization rules
        value: Value to potentially colorize

    Returns:
        Potentially colorized value with Rich markup
    """
    if any(
        keyword in column.lower() for keyword in ["status", "state", "health"]
    ):
        value_lower = value.lower()
        green_statuses = {
            "active",
            "healthy",
            "succeeded",
            "completed",
            "verified",
        }
        yellow_statuses = {
            "running",
            "pending",
            "initializing",
            "starting",
            "warning",
            "creating",
            "updating",
        }
        red_statuses = {
            "failed",
            "error",
            "unhealthy",
            "stopped",
            "crashed",
            "deleted",
        }

        if value_lower in green_statuses:
            return f"[green]{value}[/green]"
        elif value_lower in yellow_statuses:
            return f"[yellow]{value}[/yellow]"
        elif value_lower in red_statuses:
            return f"[red]{value}[/red]"

        return value

    stripped = value.strip()
    if stripped in ("-", ""):
        display = stripped or "-"
        return f"[dim]{display}[/dim]"

    return value


def _is_id_column(name: str) -> bool:
    """Check if column name should be treated as an ID column.

    Args:
        name: Column name to check

    Returns:
        True if this is an ID column (word boundary matching)
    """
    lower = name.lower().strip()
    return lower == "id" or lower.endswith(" id") or lower.endswith("_id")


def _is_name_column(name: str) -> bool:
    """Check if column name should be treated as a NAME column.

    Args:
        name: Column name to check

    Returns:
        True if this is a NAME column (word boundary matching)
    """
    lower = name.lower().strip()
    return (
        lower == "name" or lower.endswith(" name") or lower.endswith("_name")
    )


def _get_user_name(user: Union[UserResponse, UUID, None]) -> str:
    """Get the name of a user.

    Args:
        user: User object (UserResponse, UUID, or None)

    Returns:
        Human-readable user name or '-' if unavailable
    """
    if not user:
        return "-"

    if isinstance(user, UserResponse):
        return str(user.name)

    return str(user)


def _extract_model_columns(
    model: BaseModel,
    columns: Optional[Sequence[str]],
    exclude_columns: Optional[Sequence[str]],
) -> List[str]:
    """Extract column names from a model following BaseIdentifiedResponse semantics.

    Args:
        model: The model to extract columns from
        columns: Optional explicit list of columns to include
        exclude_columns: Optional list of columns to exclude

    Returns:
        List of column names to display
    """
    exclude_list = list(exclude_columns or [])

    if columns:
        return list(columns)

    if isinstance(model, BaseIdentifiedResponse):
        include_columns: List[str] = ["id"]

        if "name" in type(model).model_fields:
            include_columns.append("name")

        include_columns.extend(
            [
                k
                for k in type(model.get_body()).model_fields.keys()
                if k not in exclude_list
            ]
        )

        if model.metadata is not None:
            include_columns.extend(
                [
                    k
                    for k in type(model.get_metadata()).model_fields.keys()
                    if k not in exclude_list
                ]
            )
        return include_columns

    return [k for k in model.model_dump().keys() if k not in exclude_list]


def _format_response_value(value: Any) -> Any:
    """Format a value for display in pydantic model tables.

    Args:
        value: The value to format

    Returns:
        Formatted value (string or list of strings)
    """
    if isinstance(value, BaseIdentifiedResponse):
        if "name" in type(value).model_fields:
            return str(getattr(value, "name"))
        return str(value.id)

    if isinstance(value, list):
        formatted_items: List[str] = []
        for v in value:
            if isinstance(v, BaseIdentifiedResponse):
                formatted_items.append(str(_format_response_value(v)))
            else:
                formatted_items.append(str(v))
        return formatted_items

    if isinstance(value, Set):
        return [str(v) for v in value]

    return str(value)


def _print_key_value_table(
    items: Dict[str, Any],
    title: Optional[str] = None,
    key_header: str = "PROPERTY",
    capitalize_keys: bool = True,
) -> None:
    """Print a simple key/value table with consistent formatting.

    Args:
        items: Dictionary of key-value pairs to display
        title: Optional table title
        key_header: Header text for the key column
        capitalize_keys: Whether to uppercase the keys
    """
    rich_table = table.Table(
        box=None,
        title=title,
        show_lines=False,
    )
    rich_table.add_column(key_header, overflow="fold")
    rich_table.add_column("VALUE", overflow="fold")

    for k, v in items.items():
        key_display = k.upper() if capitalize_keys else str(k)
        rich_table.add_row(key_display, str(v))

    console.print(rich_table)
