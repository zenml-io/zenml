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
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
)

import click
from pydantic import ValidationError
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.annotator import register_annotator_subcommands
from zenml.cli.cli import TagGroup, cli
from zenml.cli.feature import register_feature_store_subcommands
from zenml.cli.model import register_model_deployer_subcommands
from zenml.cli.secret import register_secrets_manager_subcommands
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.constants import MANDATORY_COMPONENT_ATTRIBUTES
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import EntityExistsError
from zenml.io import fileio
from zenml.repository import Repository
from zenml.stack import StackComponent
from zenml.utils.analytics_utils import AnalyticsEvent, track_event
from zenml.utils.source_utils import validate_flavor_source
from zenml.zen_stores.models.component_wrapper import ComponentWrapper

if TYPE_CHECKING:
    pass


def _get_required_attributes(
    component_class: Type[StackComponent],
) -> List[str]:
    """Gets the required properties for a stack component.

    Args:
        component_class: Class of the component to get the required properties
            for.

    Returns:
        A list of the required properties for the given component class.
    """
    return [
        field_name
        for field_name, field in component_class.__fields__.items()
        if (field.required is True)
        and field_name not in MANDATORY_COMPONENT_ATTRIBUTES
    ]


def _get_available_attributes(
    component_class: Type[StackComponent],
) -> List[str]:
    """Gets the available non-mandatory properties for a stack component.

    Args:
        component_class: Class of the component to get the available
            properties for.

    Returns:
        A list of the available properties for the given component class.
    """
    return [
        field_name
        for field_name, _ in component_class.__fields__.items()
        if field_name not in MANDATORY_COMPONENT_ATTRIBUTES
    ]


def _get_optional_attributes(
    component_class: Type[StackComponent],
) -> List[str]:
    """Gets the optional properties for a stack component.

    Args:
        component_class: Class of the component to get the optional properties
            for.

    Returns:
        A list of the optional properties for the given component class.
    """
    return [
        field_name
        for field_name, field in component_class.__fields__.items()
        if field.required is False
        and field_name not in MANDATORY_COMPONENT_ATTRIBUTES
    ]


def _component_display_name(
    component_type: StackComponentType, plural: bool = False
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


def _get_stack_component_wrapper(
    component_type: StackComponentType,
    component_name: Optional[str] = None,
) -> Tuple[Optional[ComponentWrapper], bool]:
    """Gets a stack component for a given type and name.

    Args:
        component_type: Type of the component to get.
        component_name: Name of the component to get. If `None`, the
            component of the active stack gets returned.

    Returns:
        A stack component of the given type and name, or None, if no stack
        component is registered for the given name and type, and a boolean
        indicating whether the component is active or not.
    """
    singular_display_name = _component_display_name(component_type)
    plural_display_name = _component_display_name(component_type, plural=True)

    repo = Repository()

    components = repo.zen_store.get_stack_components(component_type)
    if len(components) == 0:
        cli_utils.warning(f"No {plural_display_name} registered.")
        return None, False

    active_stack = repo.zen_store.get_stack(name=repo.active_stack_name)
    active_component = active_stack.get_component_wrapper(component_type)

    if component_name:
        try:
            return (
                repo.zen_store.get_stack_component(
                    component_type, name=component_name
                ),
                (
                    active_component is not None
                    and component_name == active_component.name
                ),
            )
        except KeyError:
            cli_utils.error(
                f"No {singular_display_name} found for name '{component_name}'."
            )
    elif active_component:
        cli_utils.declare(
            f"No component name given; using `{active_component.name}` "
            f"from active stack."
        )
        return active_component, True
    else:
        cli_utils.error(f"No {singular_display_name} in active stack.")


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
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        active_stack = Repository().active_stack
        component = active_stack.components.get(component_type, None)
        display_name = _component_display_name(component_type)
        if component:
            cli_utils.declare(f"Active {display_name}: '{component.name}'")
        else:
            cli_utils.warning(
                f"No {display_name} set for active stack "
                f"('{active_stack.name}')."
            )

    return get_stack_component_command


def generate_stack_component_describe_command(
    component_type: StackComponentType,
) -> Callable[[Optional[str]], None]:
    """Generates a `describe` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument(
        "name",
        type=str,
        required=False,
    )
    def describe_stack_component_command(name: Optional[str]) -> None:
        """Prints details about the active/specified component.

        Args:
            name: Name of the component to describe.
        """
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        singular_display_name = _component_display_name(component_type)
        component_wrapper, is_active = _get_stack_component_wrapper(
            component_type, component_name=name
        )
        if component_wrapper is None:
            return

        cli_utils.print_stack_component_configuration(
            component_wrapper, singular_display_name, is_active
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
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        repo = Repository()

        components = repo.zen_store.get_stack_components(component_type)
        display_name = _component_display_name(component_type, plural=True)
        if len(components) == 0:
            cli_utils.warning(f"No {display_name} registered.")
            return
        active_stack = repo.zen_store.get_stack(name=repo.active_stack_name)
        active_component_name = None
        active_component = active_stack.get_component_wrapper(component_type)
        if active_component:
            active_component_name = active_component.name

        cli_utils.print_stack_component_list(
            components, active_component_name=active_component_name
        )

    return list_stack_components_command


def _register_stack_component(
    component_type: StackComponentType,
    component_name: str,
    component_flavor: str,
    **kwargs: Any,
) -> None:
    """Register a stack component.

    Args:
        component_type: Type of the component to register.
        component_name: Name of the component to register.
        component_flavor: Flavor of the component to register.
        **kwargs: Additional arguments to pass to the component.
    """
    repo = Repository()
    flavor_class = repo.get_flavor(
        name=component_flavor, component_type=component_type
    )
    component = flavor_class(name=component_name, **kwargs)
    Repository().register_stack_component(component)


def generate_stack_component_register_command(
    component_type: StackComponentType,
) -> Callable[[str, str, str, bool, List[str]], None]:
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
        required=True,
    )
    @click.option(
        "--flavor",
        "-f",
        "flavor",
        help=f"The flavor of the {display_name} to register.",
        type=str,
    )
    @click.option(
        "--type",
        "-t",
        "old_flavor",
        help=f"DEPRECATED: The flavor of the {display_name} to register.",
        type=str,
    )
    @click.option(
        "--interactive",
        "-i",
        "interactive",
        is_flag=True,
        help="Use interactive mode to update the secret values.",
        type=click.BOOL,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def register_stack_component_command(
        name: str,
        flavor: str,
        old_flavor: str,
        interactive: bool,
        args: List[str],
    ) -> None:
        """Registers a stack component.

        Args:
            name: Name of the component to register.
            flavor: Flavor of the component to register.
            old_flavor: DEPRECATED: The flavor of the component to register.
            interactive: Use interactive mode to fill missing values.
            args: Additional arguments to pass to the component.
        """
        cli_utils.print_active_profile()
        if flavor or old_flavor:
            if old_flavor:
                if flavor:
                    cli_utils.error(
                        f"You have used both '--type': {old_flavor} and a "
                        f"'--flavor': {flavor}, which is not allowed. "
                        f"The option '--type' will soon be DEPRECATED and "
                        f"please just use the option '--flavor' to specify "
                        f"the flavor."
                    )
                flavor = old_flavor
                cli_utils.warning(
                    "The option '--type'/'-t' will soon be DEPRECATED, please "
                    "use '--flavor'/'-f' instead. "
                )
        else:
            cli_utils.error(
                "Please use the option to specify '--flavor'/'-f' of the "
                f"{display_name} you want to register."
            )

        try:
            parsed_args = cli_utils.parse_unknown_options(
                args, expand_args=True
            )
        except AssertionError as e:
            cli_utils.error(str(e))
            return

        try:
            with console.status(f"Registering {display_name} '{name}'...\n"):
                _register_stack_component(
                    component_type=component_type,
                    component_name=name,
                    component_flavor=flavor,
                    **parsed_args,
                )
        except ValidationError as e:
            if not interactive:
                cli_utils.error(
                    f"When you are registering a new {display_name} with the "
                    f"flavor `{flavor}`, make sure that you are utilizing "
                    f"the right attributes. Current problems:\n\n{e}"
                )
                return
            else:
                cli_utils.warning(
                    f"You did not set all required fields for a "
                    f"{flavor} {display_name}. You'll be guided through the "
                    f"missing fields now. You'll be able to skip optional "
                    f"fields by just pressing enter. To cancel simply interrupt"
                    f" with CTRL+C."
                )

                repo = Repository()
                flavor_class = repo.get_flavor(
                    name=flavor, component_type=component_type
                )
                missing_fields = {
                    k: v.required
                    for k, v in flavor_class.__fields__.items()
                    if v.name not in ["name", "uuid", *parsed_args.keys()]
                }

                completed_fields = parsed_args.copy()
                for field, field_req in missing_fields.items():
                    if field_req:
                        user_input = click.prompt(f"{field}")
                    else:
                        prompt = f"{field} (Optional)'"
                        user_input = click.prompt(prompt, default="")
                    if user_input:
                        completed_fields[field] = user_input

                try:
                    with console.status(
                        f"Registering {display_name} '{name}'" f"...\n"
                    ):

                        _register_stack_component(
                            component_type=component_type,
                            component_name=name,
                            component_flavor=flavor,
                            **completed_fields,
                        )
                except Exception as e:
                    cli_utils.error(str(e))

        except Exception as e:
            cli_utils.error(str(e))

        cli_utils.declare(f"Successfully registered {display_name} `{name}`.")

    return register_stack_component_command


def generate_stack_component_flavor_register_command(
    component_type: StackComponentType,
) -> Callable[[str], None]:
    """Generates a `register` command for the flavors of a stack component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

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
        cli_utils.print_active_profile()

        # Check whether the module exists and is the right type
        try:
            component_class = validate_flavor_source(
                source=source, component_type=component_type
            )
        except ValueError as e:
            error_message = str(e) + "\n\n"
            repo_root = Repository().root

            if repo_root:
                error_message += (
                    "Please make sure your source is either importable from an "
                    "installed package or specified relative to your ZenML "
                    f"repository root '{repo_root}'."
                )

            else:
                error_message += (
                    "Please make sure your source is either importable from an "
                    "installed package or create a ZenML repository by running "
                    "`zenml init` and specify the source relative to the "
                    "repository directory. Check out "
                    "https://docs.zenml.io/developer-guide/stacks-profiles-repositories/repository "
                    "for more information."
                )

            cli_utils.error(error_message)

        # Register the flavor in the given source
        try:
            Repository().zen_store.create_flavor(
                name=component_class.FLAVOR,
                stack_component_type=component_class.TYPE,
                source=source,
            )
        except EntityExistsError as e:
            cli_utils.error(str(e))
        else:
            cli_utils.declare(
                f"Successfully registered new flavor "
                f"'{component_class.FLAVOR}' for stack component "
                f"'{component_class.TYPE}'."
            )

    return register_stack_component_flavor_command


def generate_stack_component_flavor_list_command(
    component_type: StackComponentType,
) -> Callable[[], None]:
    """Generates a `list` command for the flavors of a stack component.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    def list_stack_component_flavor_command() -> None:
        """Adds a flavor for a stack component type."""
        cli_utils.print_active_profile()

        from zenml.stack.flavor_registry import flavor_registry

        # List all the flavors of the component type
        zenml_flavors = [
            f
            for f in flavor_registry.get_flavors_by_type(
                component_type=component_type
            ).values()
        ]

        custom_flavors = Repository().zen_store.get_flavors_by_type(
            component_type=component_type
        )

        cli_utils.print_flavor_list(
            zenml_flavors + custom_flavors, component_type=component_type
        )

    return list_stack_component_flavor_command


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
        "name",
        type=str,
        required=False,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def update_stack_component_command(
        name: Optional[str], args: Sequence[str]
    ) -> None:
        """Updates a stack component.

        Args:
            name: The name of the stack component to update.
            args: Additional arguments to pass to the update command.
        """
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        kwargs = list(args)
        if name and name.startswith("--"):
            kwargs.append(name)
            name = None

        component_wrapper, _ = _get_stack_component_wrapper(
            component_type, component_name=name
        )
        if component_wrapper is None:
            return

        name = component_wrapper.name
        with console.status(f"Updating {display_name} '{name}'...\n"):
            repo = Repository()

            try:
                parsed_args = cli_utils.parse_unknown_options(
                    kwargs, expand_args=True
                )
            except AssertionError as e:
                cli_utils.error(str(e))
                return
            for prop in MANDATORY_COMPONENT_ATTRIBUTES:
                if prop in parsed_args:
                    cli_utils.error(
                        f"Cannot update mandatory property '{prop}' of "
                        f"'{name}' {component_wrapper.type}. "
                    )

            component_class = repo.get_flavor(
                name=component_wrapper.flavor,
                component_type=component_type,
            )

            available_properties = _get_available_attributes(component_class)
            for prop in parsed_args.keys():
                if (prop not in available_properties) and (
                    len(available_properties) > 0
                ):
                    cli_utils.error(
                        f"You cannot update the {display_name} "
                        f"`{component_wrapper.name}` with property "
                        f"'{prop}'. You can only update the following "
                        f"properties: {available_properties}."
                    )
                elif prop not in available_properties:
                    cli_utils.error(
                        f"You cannot update the {display_name} "
                        f"`{component_wrapper.name}` with property "
                        f"'{prop}' as this {display_name} has no optional "
                        f"properties that can be configured."
                    )
                else:
                    continue

            # Initialize a new component object to make sure pydantic validation
            # is used
            new_attributes = {
                **component_wrapper.to_component().dict(),
                **parsed_args,
            }
            updated_component = component_class(**new_attributes)

            repo.update_stack_component(
                name, updated_component.TYPE, updated_component
            )
            cli_utils.declare(f"Successfully updated {display_name} `{name}`.")

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
        "name",
        type=str,
        required=True,
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def remove_attribute_stack_component_command(
        name: str, args: List[str]
    ) -> None:
        """Removes one or more attributes from a stack component.

        Args:
            name: The name of the stack component to remove the attribute from.
            args: Additional arguments to pass to the remove_attribute command.
        """
        cli_utils.print_active_profile()
        with console.status(f"Updating {display_name} '{name}'...\n"):
            repo = Repository()
            current_component = repo.get_stack_component(component_type, name)
            if current_component is None:
                cli_utils.error(f"No {display_name} found for name '{name}'.")

            try:
                parsed_args = cli_utils.parse_unknown_component_attributes(args)
            except AssertionError as e:
                cli_utils.error(str(e))
                return

            optional_attributes = _get_optional_attributes(
                current_component.__class__
            )
            required_attributes = _get_required_attributes(
                current_component.__class__
            )

            for arg in parsed_args:
                if (
                    arg in required_attributes
                    or arg in MANDATORY_COMPONENT_ATTRIBUTES
                ):
                    cli_utils.error(
                        f"Cannot remove mandatory attribute '{arg}' of "
                        f"'{name}' {current_component.TYPE}. "
                    )
                elif arg not in optional_attributes:
                    cli_utils.error(
                        f"You cannot remove the attribute '{arg}' of "
                        f"'{name}' {current_component.TYPE}. \n"
                        f"You can only remove the following optional "
                        f"attributes: "
                        f"'{', '.join(optional_attributes)}'."
                    )

            # Remove the attributes from the current component dict
            new_attributes = {
                **current_component.dict(),
                **{arg: None for arg in parsed_args},
            }

            updated_component = current_component.__class__(**new_attributes)

            repo.update_stack_component(
                name, updated_component.TYPE, updated_component
            )
            cli_utils.declare(f"Successfully updated {display_name} `{name}`.")

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
        "name",
        type=str,
        required=True,
    )
    @click.argument(
        "new_name",
        type=str,
        required=True,
    )
    def rename_stack_component_command(name: str, new_name: str) -> None:
        """Rename a stack component.

        Args:
            name: The name of the stack component to rename.
            new_name: The new name of the stack component.
        """
        cli_utils.print_active_profile()
        with console.status(f"Renaming {display_name} '{name}'...\n"):
            repo = Repository()
            current_component = repo.get_stack_component(component_type, name)
            if current_component is None:
                cli_utils.error(f"No {display_name} found for name '{name}'.")

            registered_components = {
                component.name
                for component in repo.get_stack_components(component_type)
            }
            if new_name in registered_components:
                cli_utils.error(
                    f"Unable to rename '{name}' {display_name} to "
                    f"'{new_name}': \nA component of type '{display_name}' "
                    f"with the name '{new_name}' already exists. \nPlease "
                    f"choose a different name."
                )

            renamed_component = current_component.copy(
                update={"name": new_name}
            )

            repo.update_stack_component(
                name=name,
                component_type=component_type,
                component=renamed_component,
            )
            cli_utils.declare(
                f"Successfully renamed {display_name} `{name}` to `{new_name}`."
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

    @click.argument("name", type=str)
    def delete_stack_component_command(name: str) -> None:
        """Deletes a stack component.

        Args:
            name: The name of the stack component to delete.
        """
        cli_utils.print_active_profile()

        with console.status(f"Deleting {display_name} '{name}'...\n"):
            Repository().deregister_stack_component(
                component_type=component_type,
                name=name,
            )
            cli_utils.declare(f"Deleted {display_name}: {name}")

    return delete_stack_component_command


def generate_stack_component_copy_command(
    component_type: StackComponentType,
) -> Callable[[str, str, Optional[str]], None]:
    """Generates a `copy` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """
    display_name = _component_display_name(component_type)

    @click.argument("source_component", type=str, required=True)
    @click.argument("target_component", type=str, required=True)
    @click.option(
        "--from",
        "source_profile_name",
        type=str,
        required=False,
        help=f"The profile from which to copy the {display_name}.",
    )
    @click.option(
        "--to",
        "target_profile_name",
        type=str,
        required=False,
        help=f"The profile to which to copy the {display_name}.",
    )
    def copy_stack_component_command(
        source_component: str,
        target_component: str,
        source_profile_name: Optional[str] = None,
        target_profile_name: Optional[str] = None,
    ) -> None:
        """Copies a stack component.

        Args:
            source_component: Name of the component to copy.
            target_component: Name of the copied component.
            source_profile_name: Name of the profile from which to copy.
            target_profile_name: Name of the profile to which to copy.
        """
        track_event(AnalyticsEvent.COPIED_STACK_COMPONENT)

        if source_profile_name:
            try:
                source_profile = GlobalConfiguration().profiles[
                    source_profile_name
                ]
            except KeyError:
                cli_utils.error(
                    f"Unable to find source profile '{source_profile_name}'."
                )
        else:
            source_profile = Repository().active_profile

        if target_profile_name:
            try:
                target_profile = GlobalConfiguration().profiles[
                    target_profile_name
                ]
            except KeyError:
                cli_utils.error(
                    f"Unable to find target profile '{target_profile_name}'."
                )
        else:
            target_profile = Repository().active_profile

        # Use different repositories for fetching/registering the stack
        # depending on the source/target profile
        source_repo = Repository(profile=source_profile)
        target_repo = Repository(profile=target_profile)

        with console.status(
            f"Copying {display_name} `{source_component}`...\n"
        ):
            try:
                component = source_repo.get_stack_component(
                    component_type=component_type, name=source_component
                )
            except KeyError:
                cli_utils.error(
                    f"{display_name.capitalize()} `{source_component}` cannot "
                    "be copied as it does not exist."
                )

            existing_component_names = {
                wrapper.name
                for wrapper in target_repo.zen_store.get_stack_components(
                    component_type=component_type
                )
            }
            if target_component in existing_component_names:
                cli_utils.error(
                    f"Can't copy {display_name} as a component with the name "
                    f"'{target_component}' already exists."
                )

            # Copy the existing component but use the new name and generate a
            # new UUID
            component_config = component.dict(exclude={"uuid"})
            component_config["name"] = target_component
            copied_component = component.__class__.parse_obj(component_config)

            target_repo.register_stack_component(copied_component)

    return copy_stack_component_command


def generate_stack_component_up_command(
    component_type: StackComponentType,
) -> Callable[[Optional[str]], None]:
    """Generates a `up` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name", type=str, required=False)
    def up_stack_component_command(name: Optional[str] = None) -> None:
        """Deploys a stack component locally.

        Args:
            name: The name of the stack component to deploy.
        """
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        component_wrapper, _ = _get_stack_component_wrapper(
            component_type, component_name=name
        )
        if component_wrapper is None:
            return
        component = component_wrapper.to_component()

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
) -> Callable[[Optional[str], bool], None]:
    """Generates a `down` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name", type=str, required=False)
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
        name: Optional[str] = None,
        force: bool = False,
        old_force: bool = False,
    ) -> None:
        """Stops/Tears down the local deployment of a stack component.

        Args:
            name: The name of the stack component to stop/deprovision.
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
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        component_wrapper, _ = _get_stack_component_wrapper(
            component_type, component_name=name
        )
        if component_wrapper is None:
            return

        component = component_wrapper.to_component()
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
) -> Callable[[Optional[str], bool], None]:
    """Generates a `logs` command for the specific stack component type.

    Args:
        component_type: Type of the component to generate the command for.

    Returns:
        A function that can be used as a `click` command.
    """

    @click.argument("name", type=str, required=False)
    @click.option(
        "--follow",
        "-f",
        is_flag=True,
        help="Follow the log file instead of just displaying the current logs.",
    )
    def stack_component_logs_command(
        name: Optional[str] = None, follow: bool = False
    ) -> None:
        """Displays stack component logs.

        Args:
            name: The name of the stack component to display logs for.
            follow: Follow the log file instead of just displaying the current
                logs.
        """
        cli_utils.print_active_profile()
        cli_utils.print_active_stack()

        component_wrapper, _ = _get_stack_component_wrapper(
            component_type, component_name=name
        )
        if component_wrapper is None:
            return

        component = component_wrapper.to_component()
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
