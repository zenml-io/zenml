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

import time
from importlib import import_module
from typing import TYPE_CHECKING, Callable, List, Optional

import click
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.annotator import register_annotator_subcommands
from zenml.cli.cli import TagGroup, cli
from zenml.cli.feature import register_feature_store_subcommands
from zenml.cli.model import register_model_deployer_subcommands
from zenml.cli.secret import register_secrets_manager_subcommands
from zenml.cli.utils import _component_display_name
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.io import fileio
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

if TYPE_CHECKING:
    pass


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
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        active_stack = Client().active_stack_model
        components = active_stack.components.get(component_type, None)
        display_name = _component_display_name(component_type)
        if components:
            cli_utils.declare(f"Active {display_name}: '{components[0].name}'")
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
        "name_or_id",
        type=str,
        required=False,
    )
    def describe_stack_component_command(name_or_id: str) -> None:
        """Prints details about the active/specified component.

        Args:
            name_or_id: Name or id of the component to describe.
        """
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()

        active_component = client.active_stack_model.components.get(
            component_type, []
        )

        if name_or_id:
            try:
                component = cli_utils.get_component_by_id_or_name_or_prefix(
                    client=client,
                    component_type=component_type,
                    id_or_name_or_prefix=name_or_id,
                )
            except KeyError as e:
                cli_utils.error(str(e))  # noqa
        else:
            if len(active_component) == 0:
                cli_utils.error(
                    f"Cannot describe any {component_type} since the active "
                    f"stack has no {component_type} and no name or id was "
                    f"provided."
                )
            component = active_component[0]

        is_active = (
            len(active_component) > 0 and component.id == active_component[0].id
        )

        cli_utils.print_stack_component_configuration(
            component=component.to_hydrated_model(), active_status=is_active
        )

    return describe_stack_component_command


def generate_stack_component_list_command(
    component_type: StackComponentType,
) -> Callable[[], None]:
    """Generates a `list` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    def list_stack_components_command() -> None:
        """Prints a table of stack components."""
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()

        components = client.list_stack_components_by_type(component_type)
        hydrated_comps = [s.to_hydrated_model() for s in components]

        cli_utils.print_components_table(
            client=client,
            component_type=component_type,
            components=hydrated_comps,
        )

    return list_stack_components_command


def generate_stack_component_register_command(
    component_type: StackComponentType,
) -> Callable[[str, str, bool, List[str]], None]:
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
        "--share",
        "share",
        is_flag=True,
        help="Use this flag to share this stack component with other users.",
        type=click.BOOL,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def register_stack_component_command(
        name: str,
        flavor: str,
        share: bool,
        args: List[str],
    ) -> None:
        """Registers a stack component.

        Args:
            name: Name of the component to register.
            flavor: Flavor of the component to register.
            share: Share the stack with other users.
            args: Additional arguments to pass to the component.
        """
        # Parse the given args
        # name is guaranteed to be set by parse_name_and_extra_arguments
        name, parsed_args = cli_utils.parse_name_and_extra_arguments(  # type: ignore[assignment]
            list(args) + [name], expand_args=True
        )

        with console.status(f"Registering {display_name} '{name}'...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()
            client = Client()

            # click<8.0.0 gives flags a default of None
            if share is None:
                share = False

            # Create a new stack component model
            from zenml.models import ComponentModel

            component_create_model = ComponentModel(
                user=client.active_user.id,
                project=client.active_project.id,
                is_shared=share,
                name=name,
                flavor=flavor,
                configuration=parsed_args,
                type=component_type,
            )

            # Register the new model
            client = Client()
            client.register_stack_component(component_create_model)

            cli_utils.declare(
                f"Successfully registered {display_name} `{name}`."
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
        "name_or_id",
        type=str,
        required=False,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def update_stack_component_command(
        name_or_id: Optional[str], args: List[str]
    ) -> None:
        """Updates a stack component.

        Args:
            name_or_id: The name or id of the stack component to update.
            args: Additional arguments to pass to the update command.
        """
        args = list(args)
        if name_or_id:
            args.append(name_or_id)
        # Parse the given args
        name_or_id, parsed_args = cli_utils.parse_name_and_extra_arguments(
            args,
            expand_args=True,
            name_mandatory=False,
        )

        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()
        if not name_or_id:
            cli_utils.declare(
                f"No name or id was provided. Trying to update the active "
                f"{display_name}."
            )
            active_stack = client.active_stack_model
            if component_type not in active_stack.components:
                cli_utils.error(
                    f"The active stack has no {display_name} and no name or id "
                    f"was provided."
                )
            name_or_id = str(active_stack.components[component_type][0].id)

        with console.status(f"Updating {display_name} '{name_or_id}'...\n"):

            # Get the existing component
            existing_component = (
                cli_utils.get_component_by_id_or_name_or_prefix(
                    client=client,
                    component_type=component_type,
                    id_or_name_or_prefix=name_or_id,
                )
            )

            # Update the existing configuration
            updated_attributes = {
                **existing_component.configuration,
                **parsed_args,
            }

            # Update the component
            client.update_stack_component(
                component=existing_component.copy(
                    update={"configuration": updated_attributes}
                )
            )

            cli_utils.declare(
                f"Successfully updated {display_name} `{name_or_id}`."
            )

    return update_stack_component_command


def generate_stack_component_share_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates an `share` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument(
        "name_or_id",
        type=str,
        required=False,
    )
    def share_stack_component_command(
        name_or_id: str,
    ) -> None:
        """Shares a stack component.

        Args:
            name_or_id: The name or id of the stack component to update.
        """
        with console.status(f"Updating {display_name} '{name_or_id}'...\n"):
            cli_utils.print_active_config()

            # Get the existing component
            client = Client()
            existing_component = (
                cli_utils.get_component_by_id_or_name_or_prefix(
                    client=client,
                    component_type=component_type,
                    id_or_name_or_prefix=name_or_id,
                )
            )

            existing_component.is_shared = True

            # Update the component
            client.update_stack_component(component=existing_component)

            cli_utils.declare(
                f"Successfully shared {display_name} " f"`{name_or_id}`."
            )

    return share_stack_component_command


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
        "name_or_id",
        type=str,
        required=True,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def remove_attribute_stack_component_command(
        name_or_id: str, args: List[str]
    ) -> None:
        """Removes one or more attributes from a stack component.

        Args:
            name_or_id: The name of the stack component to remove the
                attribute from.
            args: Additional arguments to pass to the remove_attribute command.
        """
        with console.status(f"Updating {display_name} '{name_or_id}'...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Parse the given args
            parsed_args = cli_utils.parse_unknown_component_attributes(args)

            # Fetch the existing component
            client = Client()

            existing_comp = cli_utils.get_component_by_id_or_name_or_prefix(
                client=client,
                component_type=component_type,
                id_or_name_or_prefix=name_or_id,
            )

            # Remove the specified attributes
            for arg in parsed_args:
                try:
                    existing_comp.configuration.pop(arg)
                except KeyError:
                    cli_utils.error(
                        f"Cannot remove non-existent attribute '{arg}' from "
                        f"{existing_comp.type} '{existing_comp.name}'"
                        f"."
                    )

            # Update the stack component
            client.update_stack_component(component=existing_comp)

            cli_utils.declare(
                f"Successfully updated {display_name} `{name_or_id}`."
            )

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
        "name_or_id",
        type=str,
        required=True,
    )
    @click.argument(
        "new_name",
        type=str,
        required=True,
    )
    def rename_stack_component_command(name_or_id: str, new_name: str) -> None:
        """Rename a stack component.

        Args:
            name_or_id: The name of the stack component to rename.
            new_name: The new name of the stack component.
        """
        with console.status(f"Renaming {display_name} '{name_or_id}'...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Fetch the existing component
            client = Client()
            existing_component = (
                cli_utils.get_component_by_id_or_name_or_prefix(
                    client=client,
                    component_type=component_type,
                    id_or_name_or_prefix=name_or_id,
                )
            )

            # Rename and update the existing component
            client.update_stack_component(
                component=existing_component.copy(update={"name": new_name}),
            )

            cli_utils.declare(
                f"Successfully renamed {display_name} `{name_or_id}` to"
                f" `{new_name}`."
            )

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

    @click.argument("name_or_id", type=str)
    def delete_stack_component_command(name_or_id: str) -> None:
        """Deletes a stack component.

        Args:
            name_or_id: The name of the stack component to delete.
        """
        with console.status(f"Deleting {display_name} '{name_or_id}'...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Fetch the existing stack component
            client = Client()
            existing_comp = cli_utils.get_component_by_id_or_name_or_prefix(
                client=client,
                component_type=component_type,
                id_or_name_or_prefix=name_or_id,
            )

            # Delete the component
            client.deregister_stack_component(existing_comp)
            cli_utils.declare(f"Deleted {display_name}: {name_or_id}")

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

    @click.argument("source_component_name_or_id", type=str, required=True)
    @click.argument("target_component", type=str, required=True)
    def copy_stack_component_command(
        source_component_name_or_id: str,
        target_component: str,
    ) -> None:
        """Copies a stack component.

        Args:
            source_component_name_or_id: Name or id prefix of the
                                         component to copy.
            target_component: Name of the copied component.
        """
        track_event(AnalyticsEvent.COPIED_STACK_COMPONENT)

        with console.status(
            f"Copying {display_name} " f"`{source_component_name_or_id}`..\n"
        ):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Fetch the stack component
            client = Client()
            existing_component = (
                cli_utils.get_component_by_id_or_name_or_prefix(
                    client=client,
                    component_type=component_type,
                    id_or_name_or_prefix=source_component_name_or_id,
                )
            )

            # Register a new one with a new name
            from zenml.models import ComponentModel

            component_create_model = ComponentModel(
                user=client.active_user.id,
                project=client.active_project.id,
                name=target_component,
                flavor=existing_component.flavor,
                configuration=existing_component.configuration,
                type=existing_component.type,
            )
            client.register_stack_component(component=component_create_model)

    return copy_stack_component_command


def generate_stack_component_up_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `up` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name_or_id", type=str, required=False)
    def up_stack_component_command(name_or_id: str) -> None:
        """Deploys a stack component locally.

        Args:
            name_or_id: The name or_id of the stack component to deploy.
        """
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()

        try:
            component_model = cli_utils.get_component_by_id_or_name_or_prefix(
                client=client,
                component_type=component_type,
                id_or_name_or_prefix=name_or_id,
            )
        except KeyError as e:
            cli_utils.error(str(e))  # noqa
            return

        from zenml.stack import StackComponent

        component = StackComponent.from_model(component_model=component_model)

        display_name = _component_display_name(component_type)

        if component.is_running:
            cli_utils.declare(
                f"Local deployment is already running for {display_name} "
                f"'{component.name}'."
            )
            return

        if not component.is_provisioned:
            cli_utils.declare(
                f"Provisioning local resources for {display_name} "
                f"'{component.name}'."
            )
            try:
                component.provision()
            except NotImplementedError:
                cli_utils.error(
                    f"Provisioning local resources not implemented for "
                    f"{display_name} '{component.name}'."
                )

        if not component.is_running:
            cli_utils.declare(
                f"Resuming local resources for {display_name} "
                f"'{component.name}'."
            )
            component.resume()

    return up_stack_component_command


def generate_stack_component_down_command(
    component_type: StackComponentType,
) -> Callable[[str, bool], None]:
    """Generates a `down` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name_or_id", type=str, required=False)
    @click.option(
        "--force",
        "-f",
        "force",
        is_flag=True,
        help="Deprovisions local resources instead of suspending them.",
    )
    @click.option(
        "--yes",
        "-y",
        "old_force",
        is_flag=True,
        help="DEPRECATED: Deprovisions local resources instead of suspending "
        "them. Use `-f/--force` instead.",
    )
    def down_stack_component_command(
        name_or_id: str,
        force: bool = False,
        old_force: bool = False,
    ) -> None:
        """Stops/Tears down the local deployment of a stack component.

        Args:
            name_or_id: The name or id of the component to stop/deprovision.
            force: Deprovision local resources instead of suspending them.
            old_force: DEPRECATED: Deprovision local resources instead of
                suspending them. Use `-f/--force` instead.
        """
        if old_force:
            force = old_force
            cli_utils.warning(
                "The `--yes` flag will soon be deprecated. Use `--force` "
                "or `-f` instead."
            )
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()
        try:
            component_model = cli_utils.get_component_by_id_or_name_or_prefix(
                client=client,
                component_type=component_type,
                id_or_name_or_prefix=name_or_id,
            )
        except KeyError as e:
            cli_utils.error(str(e))  # noqa
            return

        from zenml.stack import StackComponent

        component = StackComponent.from_model(component_model=component_model)

        display_name = _component_display_name(component_type)

        if not force:
            if not component.is_suspended:
                cli_utils.declare(
                    f"Suspending local resources for {display_name} "
                    f"'{component.name}'."
                )
                try:
                    component.suspend()
                except NotImplementedError:
                    cli_utils.error(
                        f"Provisioning local resources not implemented for "
                        f"{display_name} '{component.name}'. If you want to "
                        f"deprovision all resources for this component, use "
                        f"the `--force/-f` flag."
                    )
            else:
                cli_utils.declare(
                    f"No running resources found for {display_name} "
                    f"'{component.name}'."
                )
        else:
            if component.is_provisioned:
                cli_utils.declare(
                    f"Deprovisioning resources for {display_name} "
                    f"'{component.name}'."
                )
                component.deprovision()
            else:
                cli_utils.declare(
                    f"No provisioned resources found for {display_name} "
                    f"'{component.name}'."
                )

    return down_stack_component_command


def generate_stack_component_logs_command(
    component_type: StackComponentType,
) -> Callable[[str, bool], None]:
    """Generates a `logs` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name_or_id", type=str, required=False)
    @click.option(
        "--follow",
        "-f",
        is_flag=True,
        help="Follow the log file instead of just displaying the current logs.",
    )
    def stack_component_logs_command(
        name_or_id: str, follow: bool = False
    ) -> None:
        """Displays stack component logs.

        Args:
            name_or_id: The name of the stack component to display logs for.
            follow: Follow the log file instead of just displaying the current
                logs.
        """
        cli_utils.print_active_config()
        cli_utils.print_active_stack()

        client = Client()
        try:
            component_model = cli_utils.get_component_by_id_or_name_or_prefix(
                client=client,
                component_type=component_type,
                id_or_name_or_prefix=name_or_id,
            )
        except KeyError as e:
            cli_utils.error(str(e))  # noqa
        else:
            from zenml.stack import StackComponent

            component = StackComponent.from_model(
                component_model=component_model
            )

            display_name = _component_display_name(component_type)
            log_file = component.log_file

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
        with console.status(f"Listing {display_name} flavors`...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Fetch the flavors
            client = Client()
            flavors = client.get_flavors_by_type(component_type=component_type)

            # Print the flavors
            cli_utils.print_flavor_list(flavors=flavors)

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
    display_name = _component_display_name(component_type)

    @click.argument(
        "source",
        type=str,
        required=True,
    )
    def register_stack_component_flavor_command(source: str) -> None:
        """Adds a flavor for a stack component type.

        Args:
            source: The source file to read the flavor from.
        """
        with console.status(f"Registering a new {display_name} flavor`...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            client = Client()

            # Create a new model
            # TODO: Investigate how we can create this model without empty
            #   strings as values for name and config_schema
            from zenml.models import FlavorModel

            flavor_create_model = FlavorModel(
                source=source,
                type=component_type,
                user=client.active_user.id,
                project=client.active_project.id,
                name="",
                config_schema="",
            )

            # Register the new model
            new_flavor = client.create_flavor(flavor_create_model)

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
        with console.status(f"Describing {display_name} flavor: {name}`...\n"):
            # Fetch the existing flavor
            client = Client()

            flavor_model = client.get_flavor_by_name_and_type(
                name=name, component_type=component_type
            )

            cli_utils.describe_pydantic_object(flavor_model.config_schema)

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
        "name",
        type=str,
        required=True,
    )
    def delete_stack_component_flavor_command(name: str) -> None:
        """Deletes a flavor.

        Args:
            name: The name of the flavor.
        """
        with console.status(f"Deleting a {display_name} flavor: {name}`...\n"):
            cli_utils.print_active_config()
            cli_utils.print_active_stack()

            # Fetch the flavor
            client = Client()
            existing_flavor = client.get_flavor_by_name_and_type(
                name=name, component_type=component_type
            )

            # Delete the flavor
            client.delete_flavor(existing_flavor)

            cli_utils.declare(
                f"Successfully deleted flavor '{existing_flavor.name}' "
                f"for stack component '{existing_flavor.type}'."
            )

    return delete_stack_component_flavor_command


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
    describe_command = generate_stack_component_describe_command(component_type)
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
    register_command = generate_stack_component_register_command(component_type)
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

    # zenml stack-component share
    share_command = generate_stack_component_share_command(component_type)
    context_settings = {"ignore_unknown_options": True}
    command_group.command(
        "share",
        context_settings=context_settings,
        help=f"Share a registered {singular_display_name}.",
    )(share_command)

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

    # zenml stack-component up
    up_command = generate_stack_component_up_command(component_type)
    command_group.command(
        "up",
        help=f"Provisions or resumes local resources for the "
        f"{singular_display_name} if possible.",
    )(up_command)

    # zenml stack-component down
    down_command = generate_stack_component_down_command(component_type)
    command_group.command(
        "down",
        help=f"Suspends resources of the local {singular_display_name} "
        f"deployment.",
    )(down_command)

    # zenml stack-component logs
    logs_command = generate_stack_component_logs_command(component_type)
    command_group.command(
        "logs", help=f"Display {singular_display_name} logs."
    )(logs_command)

    # zenml stack-component explain
    explain_command = generate_stack_component_explain_command(component_type)
    command_group.command(
        "explain", help=f"Explaining the {plural_display_name}."
    )(explain_command)

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
        help=f"Identify a new flavor for {plural_display_name}.",
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


register_all_stack_component_cli_commands()
register_annotator_subcommands()
register_secrets_manager_subcommands()
register_feature_store_subcommands()
register_model_deployer_subcommands()
