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
"""Functionality to generate stack component CLI commands."""

import os
import random
import string
import time
from importlib import import_module
from typing import Any, Callable, List, Optional, Tuple, cast
from uuid import UUID

import click
from rich.markdown import Markdown

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.cli import utils as cli_utils
from zenml.cli.annotator import register_annotator_subcommands
from zenml.cli.cli import TagGroup, cli
from zenml.cli.feature import register_feature_store_subcommands
from zenml.cli.model_registry import register_model_registry_subcommands
from zenml.cli.served_model import register_model_deployer_subcommands
from zenml.cli.utils import (
    _component_display_name,
    is_sorted_or_filtered,
    list_options,
    print_model_url,
    print_page_info,
)
from zenml.client import Client
from zenml.console import console
from zenml.constants import ALPHA_MESSAGE, STACK_RECIPE_MODULAR_RECIPES
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import AuthorizationException, IllegalOperationError
from zenml.io import fileio
from zenml.models import (
    ComponentFilter,
    ServiceConnectorResourcesModel,
)
from zenml.utils import source_utils
from zenml.utils.dashboard_utils import get_component_url
from zenml.utils.io_utils import create_dir_recursive_if_not_exists
from zenml.utils.mlstacks_utils import (
    convert_click_params_to_mlstacks_primitives,
    convert_mlstacks_primitives_to_dicts,
    import_new_mlstacks_component,
    verify_spec_and_tf_files_exist,
)
from zenml.utils.yaml_utils import write_yaml


def generate_stack_component_get_command(
    component_type: StackComponentType,
) -> Callable[[], None]:
    """Generates a `get` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    def get_stack_component_command() -> None:
        """Prints the name of the active component."""
        client = Client()
        display_name = _component_display_name(component_type)

        with console.status(f"Getting the active `{display_name}`...\n"):
            active_stack = client.active_stack_model
            components = active_stack.components.get(component_type, None)

            if components:
                cli_utils.declare(
                    f"Active {display_name}: '{components[0].name}'"
                )
                print_model_url(get_component_url(components[0]))
            else:
                cli_utils.warning(
                    f"No {display_name} set for active stack "
                    f"('{active_stack.name}')."
                )

    return get_stack_component_command


def generate_stack_component_describe_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `describe` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=False,
    )
    def describe_stack_component_command(name_id_or_prefix: str) -> None:
        """Prints details about the active/specified component.

        Args:
            name_id_or_prefix: Name or id of the component to describe.
        """
        client = Client()
        try:
            component_ = client.get_stack_component(
                name_id_or_prefix=name_id_or_prefix,
                component_type=component_type,
            )
        except KeyError as err:
            cli_utils.error(str(err))

        with console.status(f"Describing component '{component_.name}'..."):
            active_component_id = None
            active_components = client.active_stack_model.components.get(
                component_type, None
            )
            if active_components:
                active_component_id = active_components[0].id

            if component_.connector:
                connector_requirements = (
                    component_.flavor.connector_requirements
                )
            else:
                connector_requirements = None

            cli_utils.print_stack_component_configuration(
                component=component_,
                active_status=component_.id == active_component_id,
                connector_requirements=connector_requirements,
            )

            print_model_url(get_component_url(component_))

    return describe_stack_component_command


def generate_stack_component_list_command(
    component_type: StackComponentType,
) -> Callable[..., None]:
    """Generates a `list` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @list_options(ComponentFilter)
    @click.pass_context
    def list_stack_components_command(
        ctx: click.Context, **kwargs: Any
    ) -> None:
        """Prints a table of stack components.

        Args:
            ctx: The click context object
            kwargs: Keyword arguments to filter the components.
        """
        client = Client()
        with console.status(f"Listing {component_type.plural}..."):
            kwargs["type"] = component_type
            components = client.list_stack_components(**kwargs)
            if not components:
                cli_utils.declare("No components found for the given filters.")
                return

            cli_utils.print_components_table(
                client=client,
                component_type=component_type,
                components=components.items,
                show_active=not is_sorted_or_filtered(ctx),
            )
            print_page_info(components)

    return list_stack_components_command


def generate_stack_component_register_command(
    component_type: StackComponentType,
) -> Callable[[str, str, List[str]], None]:
    """Generates a `register` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name",
        type=str,
    )
    @click.option(
        "--flavor",
        "-f",
        "flavor",
        help=f"The flavor of the {display_name} to register.",
        required=True,
        type=str,
    )
    @click.option(
        "--label",
        "-l",
        "labels",
        help="Labels to be associated with the component, in the form "
        "-l key1=value1 -l key2=value2.",
        multiple=True,
    )
    @click.option(
        "--connector",
        "-c",
        "connector",
        help="Use this flag to connect this stack component to a service connector.",
        type=str,
    )
    @click.option(
        "--resource-id",
        "-r",
        "resource_id",
        help="The resource ID to use with the connector. Only required for "
        "multi-instance connectors that are not already configured with a "
        "particular resource ID.",
        required=False,
        type=str,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def register_stack_component_command(
        name: str,
        flavor: str,
        args: List[str],
        labels: Optional[List[str]] = None,
        connector: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Registers a stack component.

        Args:
            name: Name of the component to register.
            flavor: Flavor of the component to register.
            args: Additional arguments to pass to the component.
            labels: Labels to be associated with the component.
            connector: Name of the service connector to connect the component to.
            resource_id: The resource ID to use with the connector.
        """
        client = Client()

        # Parse the given args
        # name is guaranteed to be set by parse_name_and_extra_arguments
        name, parsed_args = cli_utils.parse_name_and_extra_arguments(  # type: ignore[assignment]
            list(args) + [name], expand_args=True
        )

        parsed_labels = cli_utils.get_parsed_labels(labels)

        if connector:
            try:
                client.get_service_connector(connector)
            except KeyError as err:
                cli_utils.error(
                    f"Could not find a connector '{connector}': " f"{str(err)}"
                )

        with console.status(f"Registering {display_name} '{name}'...\n"):
            # Create a new stack component model
            component = client.create_stack_component(
                name=name,
                flavor=flavor,
                component_type=component_type,
                configuration=parsed_args,
                labels=parsed_labels,
            )

            cli_utils.declare(
                f"Successfully registered {component.type} `{component.name}`."
            )
            print_model_url(get_component_url(component))

        if connector:
            connect_stack_component_with_service_connector(
                component_type=component_type,
                name_id_or_prefix=name,
                connector=connector,
                interactive=False,
                no_verify=False,
                resource_id=resource_id,
            )

    return register_stack_component_command


def generate_stack_component_update_command(
    component_type: StackComponentType,
) -> Callable[[str, List[str]], None]:
    """Generates an `update` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=False,
    )
    @click.option(
        "--label",
        "-l",
        "labels",
        help="Labels to be associated with the component, in the form "
        "-l key1=value1 -l key2=value2.",
        multiple=True,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def update_stack_component_command(
        name_id_or_prefix: Optional[str],
        args: List[str],
        labels: Optional[List[str]] = None,
    ) -> None:
        """Updates a stack component.

        Args:
            name_id_or_prefix: The name or id of the stack component to update.
            args: Additional arguments to pass to the update command.
            labels: Labels to be associated with the component.
        """
        client = Client()

        # Parse the given args
        args = list(args)
        if name_id_or_prefix:
            args.append(name_id_or_prefix)

        name_or_id, parsed_args = cli_utils.parse_name_and_extra_arguments(
            args,
            expand_args=True,
            name_mandatory=False,
        )

        parsed_labels = cli_utils.get_parsed_labels(labels)

        with console.status(f"Updating {display_name}...\n"):
            try:
                updated_component = client.update_stack_component(
                    name_id_or_prefix=name_or_id,
                    component_type=component_type,
                    configuration=parsed_args,
                    labels=parsed_labels,
                )
            except KeyError as err:
                cli_utils.error(str(err))

            cli_utils.declare(
                f"Successfully updated {display_name} "
                f"`{updated_component.name}`."
            )
            print_model_url(get_component_url(updated_component))

    return update_stack_component_command


def generate_stack_component_remove_attribute_command(
    component_type: StackComponentType,
) -> Callable[[str, List[str]], None]:
    """Generates `remove_attribute` command for a specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=True,
    )
    @click.option(
        "--label",
        "-l",
        "labels",
        help="Labels to be removed from the component.",
        multiple=True,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def remove_attribute_stack_component_command(
        name_id_or_prefix: str,
        args: List[str],
        labels: Optional[List[str]] = None,
    ) -> None:
        """Removes one or more attributes from a stack component.

        Args:
            name_id_or_prefix: The name of the stack component to remove the
                attribute from.
            args: Additional arguments to pass to the remove_attribute command.
            labels: Labels to be removed from the component.
        """
        client = Client()

        with console.status(
            f"Updating {display_name} '{name_id_or_prefix}'...\n"
        ):
            try:
                updated_component = client.update_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                    configuration={k: None for k in args},
                    labels={k: None for k in labels} if labels else None,
                )
            except (KeyError, IllegalOperationError) as err:
                cli_utils.error(str(err))

            cli_utils.declare(
                f"Successfully updated {display_name} `{name_id_or_prefix}`."
            )
            print_model_url(get_component_url(updated_component))

    return remove_attribute_stack_component_command


def generate_stack_component_rename_command(
    component_type: StackComponentType,
) -> Callable[[str, str], None]:
    """Generates a `rename` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=True,
    )
    @click.argument(
        "new_name",
        type=str,
        required=True,
    )
    def rename_stack_component_command(
        name_id_or_prefix: str, new_name: str
    ) -> None:
        """Rename a stack component.

        Args:
            name_id_or_prefix: The name of the stack component to rename.
            new_name: The new name of the stack component.
        """
        client = Client()

        with console.status(
            f"Renaming {display_name} '{name_id_or_prefix}'...\n"
        ):
            try:
                updated_component = client.update_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                    name=new_name,
                )
            except (KeyError, IllegalOperationError) as err:
                cli_utils.error(str(err))

            cli_utils.declare(
                f"Successfully renamed {display_name} `{name_id_or_prefix}` to"
                f" `{new_name}`."
            )
            print_model_url(get_component_url(updated_component))

    return rename_stack_component_command


def generate_stack_component_delete_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `delete` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument("name_id_or_prefix", type=str)
    def delete_stack_component_command(name_id_or_prefix: str) -> None:
        """Deletes a stack component.

        Args:
            name_id_or_prefix: The name of the stack component to delete.
        """
        client = Client()

        with console.status(
            f"Deleting {display_name} '{name_id_or_prefix}'...\n"
        ):
            try:
                client.delete_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                )
            except (KeyError, IllegalOperationError) as err:
                cli_utils.error(str(err))
            cli_utils.declare(f"Deleted {display_name}: {name_id_or_prefix}")

    return delete_stack_component_command


def generate_stack_component_copy_command(
    component_type: StackComponentType,
) -> Callable[[str, str], None]:
    """Generates a `copy` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "source_component_name_id_or_prefix", type=str, required=True
    )
    @click.argument("target_component", type=str, required=True)
    def copy_stack_component_command(
        source_component_name_id_or_prefix: str,
        target_component: str,
    ) -> None:
        """Copies a stack component.

        Args:
            source_component_name_id_or_prefix: Name or id prefix of the
                                         component to copy.
            target_component: Name of the copied component.
        """
        client = Client()

        with console.status(
            f"Copying {display_name} "
            f"`{source_component_name_id_or_prefix}`..\n"
        ):
            try:
                component_to_copy = client.get_stack_component(
                    name_id_or_prefix=source_component_name_id_or_prefix,
                    component_type=component_type,
                )
            except KeyError as err:
                cli_utils.error(str(err))

            copied_component = client.create_stack_component(
                name=target_component,
                flavor=component_to_copy.flavor_name,
                component_type=component_to_copy.type,
                configuration=component_to_copy.configuration,
                labels=component_to_copy.labels,
                component_spec_path=component_to_copy.component_spec_path,
            )
            print_model_url(get_component_url(copied_component))

    return copy_stack_component_command


def generate_stack_component_logs_command(
    component_type: StackComponentType,
) -> Callable[[str, bool], None]:
    """Generates a `logs` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument("name_id_or_prefix", type=str, required=False)
    @click.option(
        "--follow",
        "-f",
        is_flag=True,
        help="Follow the log file instead of just displaying the current logs.",
    )
    def stack_component_logs_command(
        name_id_or_prefix: str, follow: bool = False
    ) -> None:
        """Displays stack component logs.

        Args:
            name_id_or_prefix: The name of the stack component to display logs
                for.
            follow: Follow the log file instead of just displaying the current
                logs.
        """
        client = Client()

        with console.status(
            f"Fetching the logs for the {display_name} "
            f"'{name_id_or_prefix}'...\n"
        ):
            try:
                component_model = client.get_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                )
            except KeyError as err:
                cli_utils.error(str(err))

            from zenml.stack import StackComponent

            component = StackComponent.from_model(
                component_model=component_model
            )
            log_file = component.log_file

            if not log_file or not fileio.exists(log_file):
                cli_utils.warning(
                    f"Unable to find log file for {display_name} "
                    f"'{name_id_or_prefix}'."
                )
                return

        if not log_file or not fileio.exists(log_file):
            cli_utils.warning(
                f"Unable to find log file for {display_name} "
                f"'{component.name}'."
            )
            return

        if follow:
            try:
                with open(log_file, "r") as f:
                    # seek to the end of the file
                    f.seek(0, 2)

                    while True:
                        line = f.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        line = line.rstrip("\n")
                        click.echo(line)
            except KeyboardInterrupt:
                cli_utils.declare(f"Stopped following {display_name} logs.")
        else:
            with open(log_file, "r") as f:
                click.echo(f.read())

    return stack_component_logs_command


def generate_stack_component_explain_command(
    component_type: StackComponentType,
) -> Callable[[], None]:
    """Generates an `explain` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    def explain_stack_components_command() -> None:
        """Explains the concept of the stack component."""
        component_module = import_module(f"zenml.{component_type.plural}")

        if component_module.__doc__ is not None:
            md = Markdown(component_module.__doc__)
            console.print(md)
        else:
            console.print(
                "The explain subcommand is yet not available for "
                "this stack component. For more information, you can "
                "visit our docs page: https://docs.zenml.io/ and "
                "stay tuned for future releases."
            )

    return explain_stack_components_command


def generate_stack_component_flavor_list_command(
    component_type: StackComponentType,
) -> Callable[[], None]:
    """Generates a `list` command for the flavors of a stack component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    def list_stack_component_flavor_command() -> None:
        """Lists the flavors for a single type of stack component."""
        client = Client()

        with console.status(f"Listing {display_name} flavors`...\n"):
            flavors = client.get_flavors_by_type(component_type=component_type)

            cli_utils.print_flavor_list(flavors=flavors)
            cli_utils.print_page_info(flavors)

    return list_stack_component_flavor_command


def generate_stack_component_flavor_register_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `register` command for the flavors of a stack component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    command_name = component_type.value.replace("_", "-")
    display_name = _component_display_name(component_type)

    @click.argument(
        "source",
        type=str,
        required=True,
    )
    def register_stack_component_flavor_command(source: str) -> None:
        """Adds a flavor for a stack component type.

        Example:
            Let's say you create an artifact store flavor class `MyArtifactStoreFlavor`
            in the file path `flavors/my_flavor.py`. You would register it as:

            ```shell
            zenml artifact-store flavor register flavors.my_flavor.MyArtifactStoreFlavor
            ```

        Args:
            source: The source path of the flavor class in dot notation format.
        """
        client = Client()

        if not client.root:
            cli_utils.warning(
                f"You're running the `zenml {command_name} flavor register` "
                "command without a ZenML repository. Your current working "
                "directory will be used as the source root relative to which "
                "the `source` argument is expected. To silence this warning, "
                "run `zenml init` at your source code root."
            )

        with console.status(f"Registering a new {display_name} flavor`...\n"):
            try:
                # Register the new model
                new_flavor = client.create_flavor(
                    source=source,
                    component_type=component_type,
                )
            except ValueError as e:
                source_root = source_utils.get_source_root()

                cli_utils.error(
                    f"Flavor registration failed! ZenML tried loading the "
                    f"module `{source}` from path `{source_root}`. If this is "
                    "not what you expect, then please ensure you have run "
                    "`zenml init` at the root of your repository.\n\n"
                    f"Original exception: {str(e)}"
                )

            cli_utils.declare(
                f"Successfully registered new flavor '{new_flavor.name}' "
                f"for stack component '{new_flavor.type}'."
            )

    return register_stack_component_flavor_command


def generate_stack_component_flavor_describe_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `describe` command for a single flavor of a component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name",
        type=str,
        required=True,
    )
    def describe_stack_component_flavor_command(name: str) -> None:
        """Describes a flavor based on its config schema.

        Args:
            name: The name of the flavor.
        """
        client = Client()

        with console.status(f"Describing {display_name} flavor: {name}`...\n"):
            flavor_model = client.get_flavor_by_name_and_type(
                name=name, component_type=component_type
            )

            cli_utils.describe_pydantic_object(flavor_model.config_schema)
            resources = flavor_model.connector_requirements
            if resources:
                resources_str = f"a '{resources.resource_type}' resource"
                cli_args = f"--resource-type {resources.resource_type}"
                if resources.connector_type:
                    resources_str += (
                        f" provided by a '{resources.connector_type}' "
                        "connector"
                    )
                    cli_args += f"--connector-type {resources.connector_type}"

                cli_utils.declare(
                    f"This flavor supports connecting to external resources "
                    f"with a Service Connector. It requires {resources_str}. "
                    "You can get a list of all available connectors and the "
                    "compatible resources that they can access by running:\n\n"
                    f"'zenml service-connector list-resources {cli_args}'\n"
                    "If no compatible Service Connectors are yet registered, "
                    "you can can register a new one by running:\n\n"
                    f"'zenml service-connector register -i'"
                )
            else:
                cli_utils.declare(
                    "This flavor does not support connecting to external "
                    "resources with a Service Connector."
                )

    return describe_stack_component_flavor_command


def generate_stack_component_flavor_delete_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `delete` command for a single flavor of a component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_or_id",
        type=str,
        required=True,
    )
    def delete_stack_component_flavor_command(name_or_id: str) -> None:
        """Deletes a flavor.

        Args:
            name_or_id: The name of the flavor.
        """
        client = Client()

        with console.status(
            f"Deleting a {display_name} flavor: {name_or_id}`...\n"
        ):
            client.delete_flavor(name_or_id)

            cli_utils.declare(f"Successfully deleted flavor '{name_or_id}'.")

    return delete_stack_component_flavor_command


def generate_stack_component_deploy_command(
    component_type: StackComponentType,
) -> Callable[
    [str, str, str, str, bool, Optional[List[str]], List[str]], None
]:
    """Generates a `deploy` command for the stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name",
        type=str,
    )
    @click.option(
        "--flavor",
        "-f",
        "flavor",
        help=f"The flavor of the {display_name} to deploy.",
        required=True,
        type=str,
    )
    @click.option(
        "--provider",
        "-p",
        "provider",
        required=True,
        type=click.Choice(STACK_RECIPE_MODULAR_RECIPES),
        help="The cloud (or local provider) to use to deploy the stack component.",
    )
    @click.option(
        "--region",
        "-r",
        "region",
        required=True,
        type=str,
        help="The region to deploy the stack component to.",
    )
    @click.option(
        "--debug-mode",
        "-d",
        "debug_mode",
        is_flag=True,
        default=False,
        help="Whether to deploy the stack component in debug mode.",
    )
    @click.option(
        "--extra-config",
        "-x",
        "extra_config",
        multiple=True,
        help="Extra configurations as key=value pairs. This option can be "
        "used multiple times.",
    )
    @click.option(
        "--tags",
        "-t",
        "tags",
        required=False,
        type=click.STRING,
        help="Pass one or more tags.",
        multiple=True,
    )
    def deploy_stack_component_command(
        name: str,
        flavor: str,
        provider: str,
        region: str,
        debug_mode: bool = False,
        tags: Optional[List[str]] = None,
        extra_config: List[str] = [],
    ) -> None:
        """Deploy a stack component.

        This function also registers the newly-deployed component.

        Args:
            name: Name of the component to register.
            flavor: Flavor of the component to register.
            provider: Cloud provider (or local) to use to deploy the stack
                component.
            region: Region to deploy the stack component to.
            debug_mode: Whether to deploy the stack component in debug mode.
            tags: Tags to be added to the component.
            extra_config: Extra configuration values to be added to the
        """
        with track_handler(
            event=AnalyticsEvent.DEPLOY_STACK_COMPONENT,
        ) as analytics_handler:
            client = Client()
            try:
                # raise error if user already has a component with the same name
                client.get_stack_component(
                    component_type=component_type,
                    name_id_or_prefix=name,
                    allow_name_prefix_match=False,
                )
                cli_utils.error(
                    f"A stack component of type '{component_type.value}' with "
                    f"the name '{name}' already exists. Please try again with "
                    f"a different component name."
                )
            except KeyError:
                pass
            from mlstacks.constants import ALLOWED_FLAVORS

            if flavor not in ALLOWED_FLAVORS[component_type.value]:
                cli_utils.error(
                    f"Flavor '{flavor}' is not supported for "
                    f"{_component_display_name(component_type, True)}. "
                    "Allowed flavors are: "
                    f"{', '.join(ALLOWED_FLAVORS[component_type.value])}."
                )

            # for cases like artifact store and container
            # registry the flavor is the same as the cloud
            if flavor in {"s3", "sagemaker", "aws"} and provider != "aws":
                cli_utils.error(
                    f"Flavor '{flavor}' is not supported for "
                    f"{_component_display_name(component_type, True)} on "
                    f"{provider}."
                )
            elif flavor in {"vertex", "gcp"} and provider != "gcp":
                cli_utils.error(
                    f"Flavor '{flavor}' is not supported for "
                    f"{_component_display_name(component_type, True)} on "
                    f"{provider}."
                )

            # if the cloud is gcp, project_id is required
            extra_config_obj = (
                dict(config.split("=") for config in extra_config)
                if extra_config
                else {}
            )
            if provider == "gcp" and "project_id" not in extra_config_obj:
                cli_utils.error(
                    "Missing Project ID. You must pass your GCP project ID to "
                    "the deploy command as part of the `--extra_config` option."
                )
            cli_utils.declare("Checking prerequisites are installed...")
            cli_utils.verify_mlstacks_prerequisites_installation()
            from mlstacks.utils import zenml_utils

            cli_utils.warning(ALPHA_MESSAGE)
            cli_params = {
                "provider": provider,
                "region": region,
                "stack_name": "".join(
                    random.choice(string.ascii_letters + string.digits)
                    for _ in range(5)
                ),
                "tags": tags,
                "extra_config": list(extra_config),
                "file": None,
                "debug_mode": debug_mode,
                component_type.value: flavor,
            }
            if component_type == StackComponentType.ARTIFACT_STORE:
                cli_params["extra_config"].append(f"bucket_name={name}")  # type: ignore[union-attr]
            stack, components = convert_click_params_to_mlstacks_primitives(
                cli_params, zenml_component_deploy=True
            )

            analytics_handler.metadata = {
                "flavor": flavor,
                "provider": provider,
                "debug_mode": debug_mode,
                "component_type": component_type.value,
            }

            cli_utils.declare("Checking flavor compatibility...")
            if not zenml_utils.has_valid_flavor_combinations(
                stack, components
            ):
                cli_utils.error(
                    "The specified stack and component flavors are not "
                    "compatible with the provider or with one another. "
                    "Please try again."
                )

            stack_dict, component_dicts = convert_mlstacks_primitives_to_dicts(
                stack, components
            )
            # write the stack and component yaml files
            from mlstacks.constants import MLSTACKS_PACKAGE_NAME

            spec_dir = os.path.join(
                click.get_app_dir(MLSTACKS_PACKAGE_NAME),
                "stack_specs",
                stack.name,
            )
            cli_utils.declare(f"Writing spec files to {spec_dir}...")
            create_dir_recursive_if_not_exists(spec_dir)

            stack_file_path = os.path.join(
                spec_dir, f"stack-{stack.name}.yaml"
            )
            write_yaml(file_path=stack_file_path, contents=stack_dict)
            for component in component_dicts:
                write_yaml(
                    file_path=os.path.join(
                        spec_dir, f"{component['name']}.yaml"
                    ),
                    contents=component,
                )

            from mlstacks.utils import terraform_utils

            cli_utils.declare("Deploying stack using Terraform...")
            terraform_utils.deploy_stack(
                stack_file_path, debug_mode=debug_mode
            )
            cli_utils.declare("Stack successfully deployed.")

            stack_name: str = cli_params["stack_name"]  # type: ignore[assignment]
            cli_utils.declare(
                f"Importing {component_type.value} component '{name}' into ZenML.."
            )
            import_new_mlstacks_component(
                stack_name=stack_name,
                component_name=name,
                provider=stack.provider,
                stack_spec_dir=spec_dir,
            )
            cli_utils.declare("Component successfully imported into ZenML.")

    return deploy_stack_component_command


def generate_stack_component_destroy_command(
    component_type: StackComponentType,
) -> Callable[[str, str, bool], None]:
    """Generates a `destroy` command for the stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=True,
    )
    @click.option(
        "--provider",
        "-p",
        "provider",
        type=click.Choice(["aws", "k3d", "gcp"]),
        required=True,
    )
    @click.option(
        "--debug-mode",
        "-d",
        "debug_mode",
        is_flag=True,
        default=False,
        help="Whether to destroy the stack component in debug mode.",
    )
    def destroy_stack_component_command(
        name_id_or_prefix: str,
        provider: str,
        debug_mode: bool = False,
    ) -> None:
        """Destroy a stack component.

        Args:
            name_id_or_prefix: Name, ID or prefix of the component to destroy.
            provider: Cloud provider (or local) where the stack was deployed.
            debug_mode: Whether to destroy the stack component in debug mode.
        """
        with track_handler(
            event=AnalyticsEvent.DESTROY_STACK_COMPONENT,
        ) as analytics_handler:
            analytics_handler.metadata = {
                "provider": provider,
                "component_type": component_type.value,
                "debug_mode": debug_mode,
            }
            client = Client()

            try:
                component = client.get_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                    allow_name_prefix_match=False,
                )
            except KeyError:
                cli_utils.error(
                    "Could not find a stack component with name or id "
                    f"'{name_id_or_prefix}'.",
                )

            # Check if the component was created by a recipe
            if not component.component_spec_path:
                cli_utils.error(
                    f"Cannot destroy stack component {component.name}. It "
                    "was not created by a recipe.",
                )

            cli_utils.verify_mlstacks_prerequisites_installation()
            from mlstacks.constants import MLSTACKS_PACKAGE_NAME

            # spec_files_dir: str = component.component_spec_path
            component_spec_path: str = component.component_spec_path
            stack_name: str = os.path.basename(
                os.path.dirname(component_spec_path)
            )
            stack_spec_path: str = os.path.join(
                os.path.dirname(component_spec_path),
                f"stack-{stack_name}.yaml",
            )
            tf_definitions_path: str = os.path.join(
                click.get_app_dir(MLSTACKS_PACKAGE_NAME),
                "terraform",
                f"{provider}-modular",
            )

            cli_utils.declare(
                "Checking Terraform definitions and spec files are present..."
            )
            verify_spec_and_tf_files_exist(
                stack_spec_path, tf_definitions_path
            )

            from mlstacks.utils import terraform_utils

            cli_utils.declare(
                f"Destroying component '{component.name}' using Terraform..."
            )
            terraform_utils.destroy_stack(
                stack_path=stack_spec_path, debug_mode=debug_mode
            )
            cli_utils.declare(
                f"Component '{component.name}' successfully destroyed."
            )

            if cli_utils.confirmation(
                f"Would you like to delete the associated ZenML "
                f"component '{component.name}'?\nThis will delete the stack "
                "component registered with ZenML."
            ):
                client.delete_stack_component(
                    name_id_or_prefix=component.id,
                    component_type=component.type,
                )
                cli_utils.declare(
                    f"Component '{component.name}' successfully deleted from ZenML."
                )

            spec_dir = os.path.dirname(stack_spec_path)
            if cli_utils.confirmation(
                f"Would you like to delete the `mlstacks` spec directory for "
                f"this component, located at {spec_dir}?"
            ):
                fileio.rmtree(spec_dir)
                cli_utils.declare(
                    f"Spec directory for component '{component.name}' successfully "
                    "deleted."
                )
            cli_utils.declare(
                f"Component '{component.name}' successfully destroyed."
            )

    return destroy_stack_component_command


def prompt_select_resource_id(
    resource_ids: List[str],
    resource_name: str,
    interactive: bool = True,
) -> str:
    """Prompts the user to select a resource ID from a list of available IDs.

    Args:
        resource_ids: A list of available resource IDs.
        resource_name: The name of the resource type to select.
        interactive: Whether to prompt the user for input or error out if
            user input is required.

    Returns:
        The selected resource ID.
    """
    if len(resource_ids) == 1:
        # Only one resource ID is available, so we can select it
        # without prompting the user
        return resource_ids[0]

    if len(resource_ids) > 1:
        resource_ids_list = "\n - " + "\n - ".join(resource_ids)
        msg = (
            f"Multiple {resource_name} resources are available for the "
            f"selected connector:\n{resource_ids_list}\n"
        )
        # User needs to select a resource ID from the list
        if not interactive:
            cli_utils.error(
                f"{msg}Please use the `--resource-id` command line "  # nosec
                f"argument to select a {resource_name} resource from the "
                "list."
            )
        resource_id = click.prompt(
            f"{msg}Please select the {resource_name} that you want to use",
            type=click.Choice(resource_ids),
            show_choices=False,
        )

        return cast(str, resource_id)

    # We should never get here, but just in case...
    cli_utils.error(
        "Could not determine which resource to use. Please select a "
        "different connector."
    )


def prompt_select_resource(
    resource_list: List[ServiceConnectorResourcesModel],
) -> Tuple[UUID, str]:
    """Prompts the user to select a resource ID from a list of resources.

    Args:
        resource_list: List of resources to select from.

    Returns:
        The ID of a selected connector and the ID of the selected resource
        instance.
    """
    if len(resource_list) == 1:
        click.echo("Only one connector has compatible resources:")
    else:
        click.echo("The following connectors have compatible resources:")

    cli_utils.print_service_connector_resource_table(resource_list)

    if len(resource_list) == 1:
        connect = click.confirm(
            "Would you like to use this connector?",
            default=True,
        )
        if not connect:
            cli_utils.error("Aborting.")
        resources = resource_list[0]
    else:
        # Prompt the user to select a connector by its name or ID
        while True:
            connector_id = click.prompt(
                "Please enter the name or ID of the connector you want "
                "to use",
                type=click.Choice(
                    [
                        str(connector.id)
                        for connector in resource_list
                        if connector.id is not None
                    ]
                    + [
                        connector.name
                        for connector in resource_list
                        if connector.name is not None
                    ]
                ),
                show_choices=False,
            )
            matches = [
                c
                for c in resource_list
                if str(c.id) == connector_id or c.name == connector_id
            ]
            if len(matches) > 1:
                cli_utils.declare(
                    f"Multiple connectors with name '{connector_id}' "
                    "were found. Please try again."
                )
            else:
                resources = matches[0]
                break

    connector_uuid = resources.id
    assert connector_uuid is not None

    assert len(resources.resources) == 1
    resource_name = resources.resources[0].resource_type
    if not isinstance(resources.connector_type, str):
        resource_type_spec = resources.connector_type.resource_type_dict[
            resource_name
        ]
        resource_name = resource_type_spec.name

    resource_id = prompt_select_resource_id(
        resources.resources[0].resource_ids or [], resource_name=resource_name
    )

    return connector_uuid, resource_id


def generate_stack_component_connect_command(
    component_type: StackComponentType,
) -> Callable[[str, str], None]:
    """Generates a `connect` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=False,
    )
    @click.option(
        "--connector",
        "-c",
        "connector",
        help="The name, ID or prefix of the connector to use.",
        required=False,
        type=str,
    )
    @click.option(
        "--resource-id",
        "-r",
        "resource_id",
        help="The resource ID to use with the connector. Only required for "
        "multi-instance connectors that are not already configured with a "
        "particular resource ID.",
        required=False,
        type=str,
    )
    @click.option(
        "--interactive",
        "-i",
        "interactive",
        is_flag=True,
        default=False,
        help="Configure a service connector resource interactively.",
        type=click.BOOL,
    )
    @click.option(
        "--no-verify",
        "no_verify",
        is_flag=True,
        default=False,
        help="Skip verification of the connector resource.",
        type=click.BOOL,
    )
    def connect_stack_component_command(
        name_id_or_prefix: Optional[str],
        connector: Optional[str] = None,
        resource_id: Optional[str] = None,
        interactive: bool = False,
        no_verify: bool = False,
    ) -> None:
        """Connect the stack component to a resource through a service connector.

        Args:
            name_id_or_prefix: The name of the stack component to connect.
            connector: The name, ID or prefix of the connector to use.
            resource_id: The resource ID to use connect to. Only
                required for multi-instance connectors that are not already
                configured with a particular resource ID.
            interactive: Configure a service connector resource interactively.
            no_verify: Do not verify whether the resource is accessible.
        """
        connect_stack_component_with_service_connector(
            component_type=component_type,
            name_id_or_prefix=name_id_or_prefix,
            connector=connector,
            resource_id=resource_id,
            interactive=interactive,
            no_verify=no_verify,
        )

    return connect_stack_component_command


def generate_stack_component_disconnect_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `disconnect` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_id_or_prefix",
        type=str,
        required=True,
    )
    def disconnect_stack_component_command(name_id_or_prefix: str) -> None:
        """Disconnect a stack component from a service connector.

        Args:
            name_id_or_prefix: The name of the stack component to disconnect.
        """
        client = Client()

        with console.status(
            f"Disconnecting service-connector from {display_name} '{name_id_or_prefix}'...\n"
        ):
            try:
                updated_component = client.update_stack_component(
                    name_id_or_prefix=name_id_or_prefix,
                    component_type=component_type,
                    disconnect=True,
                )
            except (KeyError, IllegalOperationError) as err:
                cli_utils.error(str(err))

            cli_utils.declare(
                f"Successfully disconnected the service-connector from {display_name} `{name_id_or_prefix}`."
            )
            print_model_url(get_component_url(updated_component))

    return disconnect_stack_component_command


def register_single_stack_component_cli_commands(
    component_type: StackComponentType, parent_group: click.Group
) -> None:
    """Registers all basic stack component CLI commands.

    Args:
        component_type: Type of the component to generate the command for.
        parent_group: The parent group to register the commands to.
    """
    command_name = component_type.value.replace("_", "-")
    singular_display_name = _component_display_name(component_type)
    plural_display_name = _component_display_name(component_type, plural=True)

    @parent_group.group(
        command_name,
        cls=TagGroup,
        help=f"Commands to interact with {plural_display_name}.",
        tag=CliCategories.STACK_COMPONENTS,
    )
    def command_group() -> None:
        """Group commands for a single stack component type."""

    # zenml stack-component get
    get_command = generate_stack_component_get_command(component_type)
    command_group.command(
        "get", help=f"Get the name of the active {singular_display_name}."
    )(get_command)

    # zenml stack-component describe
    describe_command = generate_stack_component_describe_command(
        component_type
    )
    command_group.command(
        "describe",
        help=f"Show details about the (active) {singular_display_name}.",
    )(describe_command)

    # zenml stack-component list
    list_command = generate_stack_component_list_command(component_type)
    command_group.command(
        "list", help=f"List all registered {plural_display_name}."
    )(list_command)

    # zenml stack-component register
    register_command = generate_stack_component_register_command(
        component_type
    )
    context_settings = {"ignore_unknown_options": True}
    command_group.command(
        "register",
        context_settings=context_settings,
        help=f"Register a new {singular_display_name}.",
    )(register_command)

    # zenml stack-component update
    update_command = generate_stack_component_update_command(component_type)
    context_settings = {"ignore_unknown_options": True}
    command_group.command(
        "update",
        context_settings=context_settings,
        help=f"Update a registered {singular_display_name}.",
    )(update_command)

    # zenml stack-component remove-attribute
    remove_attribute_command = (
        generate_stack_component_remove_attribute_command(component_type)
    )
    context_settings = {"ignore_unknown_options": True}
    command_group.command(
        "remove-attribute",
        context_settings=context_settings,
        help=f"Remove attributes from a registered {singular_display_name}.",
    )(remove_attribute_command)

    # zenml stack-component rename
    rename_command = generate_stack_component_rename_command(component_type)
    command_group.command(
        "rename", help=f"Rename a registered {singular_display_name}."
    )(rename_command)

    # zenml stack-component delete
    delete_command = generate_stack_component_delete_command(component_type)
    command_group.command(
        "delete", help=f"Delete a registered {singular_display_name}."
    )(delete_command)

    # zenml stack-component copy
    copy_command = generate_stack_component_copy_command(component_type)
    command_group.command(
        "copy", help=f"Copy a registered {singular_display_name}."
    )(copy_command)

    # zenml stack-component logs
    logs_command = generate_stack_component_logs_command(component_type)
    command_group.command(
        "logs", help=f"Display {singular_display_name} logs."
    )(logs_command)

    # zenml stack-component connect
    connect_command = generate_stack_component_connect_command(component_type)
    command_group.command(
        "connect",
        help=f"Connect {singular_display_name} to a service connector.",
    )(connect_command)

    # zenml stack-component connect
    disconnect_command = generate_stack_component_disconnect_command(
        component_type
    )
    command_group.command(
        "disconnect",
        help=f"Disconnect {singular_display_name} from a service connector.",
    )(disconnect_command)

    # zenml stack-component explain
    explain_command = generate_stack_component_explain_command(component_type)
    command_group.command(
        "explain", help=f"Explaining the {plural_display_name}."
    )(explain_command)

    # zenml stack-component deploy
    deploy_command = generate_stack_component_deploy_command(component_type)
    context_settings = {"ignore_unknown_options": True}
    command_group.command(
        "deploy",
        context_settings=context_settings,
        help=f"Deploy a new {singular_display_name}.",
    )(deploy_command)

    # zenml stack-component destroy
    destroy_command = generate_stack_component_destroy_command(component_type)
    command_group.command(
        "destroy",
        help=f"Destroy an existing {singular_display_name}.",
    )(destroy_command)

    # zenml stack-component flavor
    @command_group.group(
        "flavor", help=f"Commands to interact with {plural_display_name}."
    )
    def flavor_group() -> None:
        """Group commands to handle flavors for a stack component type."""

    # zenml stack-component flavor register
    register_flavor_command = generate_stack_component_flavor_register_command(
        component_type=component_type
    )
    flavor_group.command(
        "register",
        help=f"Register a new {singular_display_name} flavor.",
    )(register_flavor_command)

    # zenml stack-component flavor list
    list_flavor_command = generate_stack_component_flavor_list_command(
        component_type=component_type
    )
    flavor_group.command(
        "list",
        help=f"List all registered flavors for {plural_display_name}.",
    )(list_flavor_command)

    # zenml stack-component flavor describe
    describe_flavor_command = generate_stack_component_flavor_describe_command(
        component_type=component_type
    )
    flavor_group.command(
        "describe",
        help=f"Describe a {singular_display_name} flavor.",
    )(describe_flavor_command)

    # zenml stack-component flavor delete
    delete_flavor_command = generate_stack_component_flavor_delete_command(
        component_type=component_type
    )
    flavor_group.command(
        "delete",
        help=f"Delete a {plural_display_name} flavor.",
    )(delete_flavor_command)


def register_all_stack_component_cli_commands() -> None:
    """Registers CLI commands for all stack components."""
    for component_type in StackComponentType:
        register_single_stack_component_cli_commands(
            component_type, parent_group=cli
        )


def connect_stack_component_with_service_connector(
    component_type: StackComponentType,
    name_id_or_prefix: Optional[str] = None,
    connector: Optional[str] = None,
    resource_id: Optional[str] = None,
    interactive: bool = False,
    no_verify: bool = False,
) -> None:
    """Connect the stack component to a resource through a service connector.

    Args:
        component_type: Type of the component to generate the command for.
        name_id_or_prefix: The name of the stack component to connect.
        connector: The name, ID or prefix of the connector to use.
        resource_id: The resource ID to use connect to. Only
            required for multi-instance connectors that are not already
            configured with a particular resource ID.
        interactive: Configure a service connector resource interactively.
        no_verify: Do not verify whether the resource is accessible.
    """
    display_name = _component_display_name(component_type)

    if not connector and not interactive:
        cli_utils.error(
            "Please provide either a connector ID or set the interactive "
            "flag."
        )

    if connector and interactive:
        cli_utils.error(
            "Please provide either a connector ID or set the interactive "
            "flag, not both."
        )

    client = Client()

    try:
        component_model = client.get_stack_component(
            name_id_or_prefix=name_id_or_prefix,
            component_type=component_type,
        )
    except KeyError as err:
        cli_utils.error(str(err))

    requirements = component_model.flavor.connector_requirements

    if not requirements:
        cli_utils.error(
            f"The '{component_model.name}' {display_name} implementation "
            "does not support using a service connector to connect to "
            "resources."
        )

    resource_type = requirements.resource_type
    if requirements.resource_id_attr is not None:
        # Check if an attribute is set in the component configuration
        resource_id = component_model.configuration.get(
            requirements.resource_id_attr
        )

    if interactive:
        # Fetch the list of connectors that have resources compatible with
        # the stack component's flavor's resource requirements
        with console.status(
            "Finding all resources matching the stack component "
            "requirements (this could take a while)...\n"
        ):
            resource_list = client.list_service_connector_resources(
                connector_type=requirements.connector_type,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        resource_list = [
            resource
            for resource in resource_list
            if resource.resources[0].resource_ids
        ]

        error_resource_list = [
            resource
            for resource in resource_list
            if not resource.resources[0].resource_ids
        ]

        if not resource_list:
            # No compatible resources were found
            additional_info = ""
            if error_resource_list:
                additional_info = (
                    f"{len(error_resource_list)} connectors can be used "
                    f"to gain access to {resource_type} resources required "
                    "for the stack component, but they are in an error "
                    "state or they didn't list any matching resources. "
                )
            command_args = ""
            if requirements.connector_type:
                command_args += (
                    f" --connector-type {requirements.connector_type}"
                )
            command_args += f" --resource-type {requirements.resource_type}"
            if resource_id:
                command_args += f" --resource-id {resource_id}"

            cli_utils.error(
                f"No compatible valid resources were found for the "
                f"'{component_model.name}' {display_name} in your "
                f"workspace. {additional_info}You can create a new "
                "connector using the 'zenml service-connector register' "
                "command or list the compatible resources using the "
                f"'zenml service-connector list-resources{command_args}' "
                "command."
            )

        # Prompt the user to select a connector and a resource ID, if
        # applicable
        connector_id, resource_id = prompt_select_resource(resource_list)
        no_verify = False
    else:
        # Non-interactive mode: we need to fetch the connector model first

        assert connector is not None
        try:
            connector_model = client.get_service_connector(connector)
        except KeyError as err:
            cli_utils.error(
                f"Could not find a connector '{connector}': " f"{str(err)}"
            )

        connector_id = connector_model.id

        satisfied, msg = requirements.is_satisfied_by(
            connector_model, component_model
        )
        if not satisfied:
            cli_utils.error(
                f"The connector with ID {connector_id} does not match the "
                f"component's `{name_id_or_prefix}` of type `{component_type}`"
                f" connector requirements: {msg}. Please pick a connector that "
                f"is compatible with the component flavor and try again, or "
                f"use the interactive mode to select a compatible connector."
            )

        if not resource_id:
            if connector_model.resource_id:
                resource_id = connector_model.resource_id
            elif connector_model.supports_instances:
                cli_utils.error(
                    f"Multiple {resource_type} resources are available for "
                    "the selected connector. Please use the "
                    "`--resource-id` command line argument to configure a "
                    f"{resource_type} resource or use the interactive mode "
                    "to select a resource interactively."
                )

    connector_resources: Optional[ServiceConnectorResourcesModel] = None
    if not no_verify:
        with console.status(
            "Validating service connector resource configuration...\n"
        ):
            try:
                connector_resources = client.verify_service_connector(
                    connector_id,
                    resource_type=requirements.resource_type,
                    resource_id=resource_id,
                )
            except (
                KeyError,
                ValueError,
                IllegalOperationError,
                NotImplementedError,
                AuthorizationException,
            ) as e:
                cli_utils.error(
                    f"Access to the resource could not be verified: {e}"
                )
        resources = connector_resources.resources[0]
        if resources.resource_ids:
            if len(resources.resource_ids) > 1:
                cli_utils.error(
                    f"Multiple {resource_type} resources are available for "
                    "the selected connector. Please use the "
                    "`--resource-id` command line argument to configure a "
                    f"{resource_type} resource or use the interactive mode "
                    "to select a resource interactively."
                )
            else:
                resource_id = resources.resource_ids[0]

    with console.status(f"Updating {display_name} '{name_id_or_prefix}'...\n"):
        try:
            client.update_stack_component(
                name_id_or_prefix=name_id_or_prefix,
                component_type=component_type,
                connector_id=connector_id,
                connector_resource_id=resource_id,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

    if connector_resources is not None:
        cli_utils.declare(
            f"Successfully connected {display_name} "
            f"`{component_model.name}` to the following resources:"
        )

        cli_utils.print_service_connector_resource_table([connector_resources])

    else:
        cli_utils.declare(
            f"Successfully connected {display_name} "
            f"`{component_model.name}` to resource."
        )


register_all_stack_component_cli_commands()
register_annotator_subcommands()
register_feature_store_subcommands()
register_model_deployer_subcommands()
register_model_registry_subcommands()
