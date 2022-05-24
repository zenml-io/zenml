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
import base64
import datetime
import os
import subprocess
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import click
import yaml
from dateutil import tz
from pydantic import BaseModel
from rich import box, table
from rich.markup import escape
from rich.prompt import Confirm
from rich.style import Style
from rich.text import Text

from zenml.console import console, zenml_style_defaults
from zenml.constants import IS_DEBUG_ENV
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.config.profile_config import ProfileConfiguration
    from zenml.enums import StackComponentType
    from zenml.integrations.integration import IntegrationMeta
    from zenml.model_deployers import BaseModelDeployer
    from zenml.secret import BaseSecretSchema
    from zenml.services import BaseService
    from zenml.zen_stores.models import ComponentWrapper, FlavorWrapper


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
    text: Union[str, Text],
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
) -> None:
    """Echo a declaration on the CLI.

    Args:
        text: Input text string.
        bold: Optional boolean to bold the text.
        italic: Optional boolean to italicize the text.
    """
    base_style = zenml_style_defaults["info"]
    style = Style.chain(base_style, Style(bold=bold, italic=italic))
    console.print(text, style=style)


def error(text: str) -> NoReturn:
    """Echo an error string on the CLI.

    Args:
      text: Input text string.

    Raises:
        click.ClickException: when called.
    """
    raise click.ClickException(message=click.style(text, fg="red", bold=True))


def warning(
    text: str,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
) -> None:
    """Echo a warning string on the CLI.

    Args:
        text: Input text string.
        bold: Optional boolean to bold the text.
        italic: Optional boolean to italicize the text.
    """
    base_style = zenml_style_defaults["warning"]
    style = Style.chain(base_style, Style(bold=bold, italic=italic))
    console.print(text, style=style)


def pretty_print(obj: Any) -> None:
    """Pretty print an object on the CLI using `rich.print`.

    Args:
      obj: Any object with a __str__ method defined.
    # TODO: [LOW] check whether this needs to be converted to a string first
    # TODO: [LOW] use rich prettyprint for this instead
    """
    console.print(obj)


def print_table(obj: List[Dict[str, Any]], **columns: table.Column) -> None:
    """Prints the list of dicts in a table format. The input object should be a
    List of Dicts. Each item in that list represent a line in the Table. Each
    dict should have the same keys. The keys of the dict will be used as
    headers of the resulting table.

    Args:
      obj: A List containing dictionaries.
      columns: Optional column configurations to be used in the table.
    """
    column_keys = {key: None for dict_ in obj for key in dict_}
    column_names = [columns.get(key, key.upper()) for key in column_keys]
    rich_table = table.Table(box=box.HEAVY_EDGE, show_lines=True)
    for col_name in column_names:
        if isinstance(col_name, str):
            rich_table.add_column(str(col_name), overflow="fold")
        else:
            rich_table.add_column(str(col_name.header).upper(), overflow="fold")
    for dict_ in obj:
        values = []
        for key in column_keys:
            if key is None:
                values.append(None)
            else:
                value = str(dict_.get(key) or " ")
                # escape text when square brackets are used
                if "[" in value:
                    value = escape(value)
                values.append(value)
        rich_table.add_row(*values)
    if len(rich_table.columns) > 1:
        rich_table.columns[0].justify = "center"
    console.print(rich_table)


M = TypeVar("M", bound=BaseModel)


def print_pydantic_models(
    models: Sequence[M],
    columns: Optional[Sequence[str]] = None,
    exclude_columns: Sequence[str] = (),
    is_active: Optional[Callable[[M], bool]] = None,
) -> None:
    """Prints the list of Pydantic models in a table.

    Args:
        models: List of pydantic models that will be represented as a row in
            the table.
        columns: Optionally specify subset and order of columns to display.
        exclude_columns: Optionally specify columns to exclude. (Note: `columns`
            takes precedence over `exclude_columns`.)
        is_active: Optional function that marks as row as active.

    """

    def __dictify(model: M) -> Dict[str, str]:
        """Helper function to map over the list to turn Models into dicts."""
        items = (
            {
                key: str(value)
                for key, value in model.dict().items()
                if key not in exclude_columns
            }
            if columns is None
            else {key: str(model.dict()[key]) for key in columns}
        )
        # prepend an active marker if a function to mark active was passed
        return (
            dict(active=":point_right:" if is_active(model) else "", **items)
            if is_active is not None
            else items
        )

    print_table([__dictify(model) for model in models])


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
                "INSTALLED": ":white_check_mark:" if is_installed else ":x:",
                "INTEGRATION": name,
                "REQUIRED_PACKAGES": ", ".join(integration_impl.REQUIREMENTS),  # type: ignore[attr-defined]
            }
        )
    return list_of_dicts


def print_stack_component_list(
    components: List["ComponentWrapper"],
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
            "NAME": component.name,
            "FLAVOR": component.flavor,
            "UUID": component.uuid,
            **{
                key.upper(): str(value)
                for key, value in yaml.safe_load(
                    base64.b64decode(component.config).decode()
                ).items()
            },
        }
        configurations.append(component_config)
    print_table(configurations)


def print_stack_configuration(
    config: Dict["StackComponentType", str], active: bool, stack_name: str
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
    rich_table.add_column("COMPONENT_TYPE", overflow="fold")
    rich_table.add_column("COMPONENT_NAME", overflow="fold")
    for component_type, name in config.items():
        rich_table.add_row(component_type.value, name)

    # capitalize entries in first column
    rich_table.columns[0]._cells = [
        component.upper()  # type: ignore[union-attr]
        for component in rich_table.columns[0]._cells
    ]
    console.print(rich_table)


def print_flavor_list(
    flavors: List["FlavorWrapper"],
    component_type: "StackComponentType",
) -> None:
    """Prints the list of flavors."""
    from zenml.integrations.registry import integration_registry
    from zenml.utils.source_utils import validate_flavor_source

    flavor_table = []
    for f in flavors:
        reachable = False

        if f.integration:
            if f.integration == "built-in":
                reachable = True
            else:
                reachable = integration_registry.is_installed(f.integration)

        else:
            try:
                validate_flavor_source(f.source, component_type=component_type)
                reachable = True
            except (
                AssertionError,
                ModuleNotFoundError,
                ImportError,
                ValueError,
            ):
                pass

        flavor_table.append(
            {
                "FLAVOR": f.name,
                "INTEGRATION": f.integration,
                "READY-TO-USE": ":white_check_mark:" if reachable else "",
                "SOURCE": f.source,
            }
        )

    print_table(flavor_table)
    warning(
        "The flag 'READY-TO-USE' indicates whether you can directly "
        "create/use/manage a stack component with that specific flavor. "
        "You can bring a flavor to a state where it is 'READY-TO-USE' in two "
        "different ways. If the flavor belongs to a ZenML integration, "
        "you can use `zenml integration install <name-of-the-integration>` and "
        "if it doesn't, you can make sure that you are using ZenML in an "
        "environment where ZenML can import the flavor through its source "
        "path (also shown in the list)."
    )


def print_stack_component_configuration(
    component: "ComponentWrapper", display_name: str, active_status: bool
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
    rich_table.add_column("VALUE", overflow="fold")

    component_dict = component.dict()
    component_dict.pop("config")
    component_dict.update(
        yaml.safe_load(base64.b64decode(component.config).decode())
    )
    items = component_dict.items()
    for item in items:
        elements = []
        for idx, elem in enumerate(item):
            if idx == 0:
                elements.append(f"{elem.upper()}")
            else:
                elements.append(str(elem))
        rich_table.add_row(*elements)

    console.print(rich_table)


def print_active_profile() -> None:
    """Print active profile."""
    from zenml.repository import Repository

    repo = Repository()
    scope = "local" if repo.root else "global"
    declare(
        f"Running with active profile: '{repo.active_profile_name}' ({scope})"
    )


def print_active_stack() -> None:
    """Print active stack."""
    from zenml.repository import Repository

    repo = Repository()
    declare(f"Running with active stack: '{repo.active_stack_name}'")


def print_profile(
    profile: "ProfileConfiguration",
    active: bool,
) -> None:
    """Prints the configuration options of a profile.

    Args:
        profile: Profile to print.
        active: Whether the profile is active.
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
    rich_table.add_column("VALUE", overflow="fold")
    items = profile.dict().items()
    for item in items:
        elements = []
        for idx, elem in enumerate(item):
            if idx == 0:
                elements.append(f"{elem.upper()}")
            else:
                elements.append(elem)
        rich_table.add_row(*elements)

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


MAX_ARGUMENT_VALUE_SIZE = 10240


def _expand_argument_value_from_file(name: str, value: str) -> str:
    """Expands the value of an argument pointing to a file into the contents of
    that file.

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
    filename = value[1:]
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


def parse_unknown_options(
    args: List[str], expand_args: bool = False
) -> Dict[str, Any]:
    """Parse unknown options from the CLI.

    Args:
        args: A list of strings from the CLI.
        expand_args: Whether to expand argument values into the contents of the
            files they may be pointing at using the special `@` character.

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

    r_args = {k: _expand_argument_value_from_file(k, v) for k, v in p_args}
    assert len(p_args) == len(r_args), "Replicated arguments!"

    if expand_args:
        r_args = {
            k: _expand_argument_value_from_file(k, v) for k, v in r_args.items()
        }

    return r_args


def parse_unknown_component_attributes(args: List[str]) -> List[str]:
    """Parse unknown options from the CLI.

    Args:
      args: A list of strings from the CLI.

    Returns:
        List of parsed args.
    """
    warning_message = (
        "Please provide args with a proper "
        "identifier as the key and the following structure: "
        "--custom_attribute"
    )

    assert all(a.startswith("--") for a in args), warning_message
    p_args = [a.lstrip("-") for a in args]
    assert all(v.isidentifier() for v in p_args), warning_message
    return p_args


def install_packages(packages: List[str]) -> None:
    """Installs pypi packages into the current environment with pip"""
    command = [sys.executable, "-m", "pip", "install"] + packages

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
    secret: "BaseSecretSchema", hide_secret: bool = True
) -> None:
    """Given a secret set print all key value pairs associated with the secret

    Args:
        secret: Secret of type BaseSecretSchema
        hide_secret: boolean that configures if the secret values are shown
            on the CLI
    """

    def get_secret_value(value: Any) -> str:
        if value is None:
            return ""
        if hide_secret:
            return "***"
        return str(value)

    stack_dicts = [
        {
            "SECRET_KEY": key,
            "SECRET_VALUE": get_secret_value(value),
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
    rich_table.add_column("SECRET_NAME", overflow="fold")
    secrets.sort()
    for item in secrets:
        rich_table.add_row(item)

    console.print(rich_table)


def get_service_status_emoji(service: "BaseService") -> str:
    """Get the rich emoji representing the operational status of a Service.

    Args:
        service: Service to get emoji for.

    Returns:
        String representing the emoji.
    """
    from zenml.services.service_status import ServiceState

    if service.status.state == ServiceState.ACTIVE:
        return ":white_check_mark:"
    if service.status.state == ServiceState.INACTIVE:
        return ":pause_button:"
    if service.status.state == ServiceState.ERROR:
        return ":heavy_exclamation_mark:"
    return ":hourglass_not_done:"


def pretty_print_model_deployer(
    model_services: List["BaseService"], model_deployer: "BaseModelDeployer"
) -> None:
    """Given a list of served_models print all key value pairs associated with
    the secret

    Args:
        model_services: list of model deployment services
        model_deployer: Active model deployer
    """
    model_service_dicts = []
    for model_service in model_services:
        served_model_info = model_deployer.get_model_server_info(model_service)
        dict_uuid = str(model_service.uuid)
        dict_pl_name = model_service.config.pipeline_name
        dict_pl_stp_name = model_service.config.pipeline_step_name
        dict_model_name = served_model_info.get("MODEL_NAME", "")
        model_service_dicts.append(
            {
                "STATUS": get_service_status_emoji(model_service),
                "UUID": dict_uuid,
                "PIPELINE_NAME": dict_pl_name,
                "PIPELINE_STEP_NAME": dict_pl_stp_name,
                "MODEL_NAME": dict_model_name,
            }
        )
    print_table(
        model_service_dicts, UUID=table.Column(header="UUID", min_width=36)
    )


def print_served_model_configuration(
    model_service: "BaseService", model_deployer: "BaseModelDeployer"
) -> None:
    """Prints the configuration of a model_service.

    Args:
        model_service: Specific service instance to
        model_deployer: Active model deployer
    """
    title = f"Properties of Served Model {model_service.uuid}"

    rich_table = table.Table(
        box=box.HEAVY_EDGE,
        title=title,
        show_lines=True,
    )
    rich_table.add_column("MODEL SERVICE PROPERTY", overflow="fold")
    rich_table.add_column("VALUE", overflow="fold")

    # Get implementation specific info
    served_model_info = model_deployer.get_model_server_info(model_service)

    served_model_info = {
        **served_model_info,
        "UUID": str(model_service.uuid),
        "STATUS": get_service_status_emoji(model_service),
        "STATUS_MESSAGE": model_service.status.last_error,
        "PIPELINE_NAME": model_service.config.pipeline_name,
        "PIPELINE_RUN_ID": model_service.config.pipeline_run_id,
        "PIPELINE_STEP_NAME": model_service.config.pipeline_step_name,
    }

    # Sort fields alphabetically
    sorted_items = {k: v for k, v in sorted(served_model_info.items())}

    for item in sorted_items.items():
        rich_table.add_row(*[str(elem) for elem in item])

    # capitalize entries in first column
    rich_table.columns[0]._cells = [
        component.upper()  # type: ignore[union-attr]
        for component in rich_table.columns[0]._cells
    ]
    console.print(rich_table)
