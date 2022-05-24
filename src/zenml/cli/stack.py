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
"""CLI for manipulating ZenML local and global config file."""

import json
from typing import Dict, Optional

import click

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.stack_components import (
    _component_display_name,
    _register_stack_component,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import ProvisioningError
from zenml.repository import Repository
from zenml.stack import Stack
from zenml.utils.analytics_utils import AnalyticsEvent, track_event
from zenml.utils.yaml_utils import read_yaml, write_yaml


# Stacks
@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
)
def stack() -> None:
    """Stacks to define various environments."""


@stack.command("register", context_settings=dict(ignore_unknown_options=True))
@click.argument("stack_name", type=str, required=True)
@click.option(
    "-m",
    "--metadata-store",
    "metadata_store_name",
    help="Name of the metadata store for this stack.",
    type=str,
    required=True,
)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store_name",
    help="Name of the artifact store for this stack.",
    type=str,
    required=True,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator_name",
    help="Name of the orchestrator for this stack.",
    type=str,
    required=True,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry_name",
    help="Name of the container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-x",
    "--secrets_manager",
    "secrets_manager_name",
    help="Name of the secrets manager for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator_name",
    help="Name of the step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store_name",
    help="Name of the feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer_name",
    help="Name of the model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker_name",
    help="Name of the experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter_name",
    help="Name of the alerter for this stack.",
    type=str,
    required=False,
)
@click.option(
    "--set",
    "set_stack",
    is_flag=True,
    help="Immediately set this stack as active.",
    type=click.BOOL,
)
def register_stack(
    stack_name: str,
    metadata_store_name: str,
    artifact_store_name: str,
    orchestrator_name: str,
    container_registry_name: Optional[str] = None,
    secrets_manager_name: Optional[str] = None,
    step_operator_name: Optional[str] = None,
    feature_store_name: Optional[str] = None,
    model_deployer_name: Optional[str] = None,
    experiment_tracker_name: Optional[str] = None,
    alerter_name: Optional[str] = None,
    set_stack: bool = False,
) -> None:
    """Register a stack."""
    cli_utils.print_active_profile()

    with console.status(f"Registering stack '{stack_name}'...\n"):
        repo = Repository()

        stack_components = {
            StackComponentType.METADATA_STORE: repo.get_stack_component(
                StackComponentType.METADATA_STORE, name=metadata_store_name
            ),
            StackComponentType.ARTIFACT_STORE: repo.get_stack_component(
                StackComponentType.ARTIFACT_STORE, name=artifact_store_name
            ),
            StackComponentType.ORCHESTRATOR: repo.get_stack_component(
                StackComponentType.ORCHESTRATOR, name=orchestrator_name
            ),
        }

        if container_registry_name:
            stack_components[
                StackComponentType.CONTAINER_REGISTRY
            ] = repo.get_stack_component(
                StackComponentType.CONTAINER_REGISTRY,
                name=container_registry_name,
            )

        if secrets_manager_name:
            stack_components[
                StackComponentType.SECRETS_MANAGER
            ] = repo.get_stack_component(
                StackComponentType.SECRETS_MANAGER,
                name=secrets_manager_name,
            )

        if step_operator_name:
            stack_components[
                StackComponentType.STEP_OPERATOR
            ] = repo.get_stack_component(
                StackComponentType.STEP_OPERATOR,
                name=step_operator_name,
            )

        if feature_store_name:
            stack_components[
                StackComponentType.FEATURE_STORE
            ] = repo.get_stack_component(
                StackComponentType.FEATURE_STORE,
                name=feature_store_name,
            )
        if model_deployer_name:
            stack_components[
                StackComponentType.MODEL_DEPLOYER
            ] = repo.get_stack_component(
                StackComponentType.MODEL_DEPLOYER,
                name=model_deployer_name,
            )

        if experiment_tracker_name:
            stack_components[
                StackComponentType.EXPERIMENT_TRACKER
            ] = repo.get_stack_component(
                StackComponentType.EXPERIMENT_TRACKER,
                name=experiment_tracker_name,
            )

        if alerter_name:
            stack_components[
                StackComponentType.ALERTER
            ] = repo.get_stack_component(
                StackComponentType.ALERTER,
                name=alerter_name,
            )

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.register_stack(stack_)
        cli_utils.declare(f"Stack '{stack_name}' successfully registered!")

    if set_stack:
        set_active_stack(stack_name=stack_name)


@stack.command("update", context_settings=dict(ignore_unknown_options=True))
@click.argument("stack_name", type=str, required=False)
@click.option(
    "-m",
    "--metadata-store",
    "metadata_store_name",
    help="Name of the new metadata store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store_name",
    help="Name of the new artifact store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator_name",
    help="Name of the new orchestrator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry_name",
    help="Name of the new container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator_name",
    help="Name of the new step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-x",
    "--secrets_manager",
    "secrets_manager_name",
    help="Name of the new secrets manager for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store_name",
    help="Name of the new feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer_name",
    help="Name of the new model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker_name",
    help="Name of the new experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter_name",
    help="Name of the new alerter for this stack.",
    type=str,
    required=False,
)
def update_stack(
    stack_name: Optional[str],
    metadata_store_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
    orchestrator_name: Optional[str] = None,
    container_registry_name: Optional[str] = None,
    step_operator_name: Optional[str] = None,
    secrets_manager_name: Optional[str] = None,
    feature_store_name: Optional[str] = None,
    model_deployer_name: Optional[str] = None,
    experiment_tracker_name: Optional[str] = None,
    alerter_name: Optional[str] = None,
) -> None:
    """Update a stack."""
    cli_utils.print_active_profile()

    repo = Repository()

    active_stack_name = repo.active_stack_name
    stack_name = stack_name or active_stack_name

    with console.status(f"Updating stack `{stack_name}`...\n"):
        repo = Repository()
        try:
            current_stack = repo.get_stack(stack_name)
        except KeyError:
            cli_utils.error(
                f"Stack `{stack_name}` cannot be updated as it does not exist.",
            )
        stack_components = current_stack.components

        if metadata_store_name:
            stack_components[
                StackComponentType.METADATA_STORE
            ] = repo.get_stack_component(
                StackComponentType.METADATA_STORE, name=metadata_store_name
            )

        if artifact_store_name:
            stack_components[
                StackComponentType.ARTIFACT_STORE
            ] = repo.get_stack_component(
                StackComponentType.ARTIFACT_STORE, name=artifact_store_name
            )

        if orchestrator_name:
            stack_components[
                StackComponentType.ORCHESTRATOR
            ] = repo.get_stack_component(
                StackComponentType.ORCHESTRATOR, name=orchestrator_name
            )

        if container_registry_name:
            stack_components[
                StackComponentType.CONTAINER_REGISTRY
            ] = repo.get_stack_component(
                StackComponentType.CONTAINER_REGISTRY,
                name=container_registry_name,
            )

        if step_operator_name:
            stack_components[
                StackComponentType.STEP_OPERATOR
            ] = repo.get_stack_component(
                StackComponentType.STEP_OPERATOR,
                name=step_operator_name,
            )

        if secrets_manager_name:
            stack_components[
                StackComponentType.SECRETS_MANAGER
            ] = repo.get_stack_component(
                StackComponentType.SECRETS_MANAGER,
                name=secrets_manager_name,
            )

        if feature_store_name:
            stack_components[
                StackComponentType.FEATURE_STORE
            ] = repo.get_stack_component(
                StackComponentType.FEATURE_STORE,
                name=feature_store_name,
            )

        if model_deployer_name:
            stack_components[
                StackComponentType.MODEL_DEPLOYER
            ] = repo.get_stack_component(
                StackComponentType.MODEL_DEPLOYER,
                name=model_deployer_name,
            )

        if experiment_tracker_name:
            stack_components[
                StackComponentType.EXPERIMENT_TRACKER
            ] = repo.get_stack_component(
                StackComponentType.EXPERIMENT_TRACKER,
                name=experiment_tracker_name,
            )

        if alerter_name:
            stack_components[
                StackComponentType.ALERTER
            ] = repo.get_stack_component(
                StackComponentType.ALERTER,
                name=alerter_name,
            )

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.update_stack(stack_name, stack_)
        cli_utils.declare(f"Stack `{stack_name}` successfully updated!")


@stack.command(
    "remove-component", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("stack_name", type=str, required=False)
@click.option(
    "-c",
    "--container_registry",
    "container_registry_flag",
    help="Include this to remove the container registry from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator_flag",
    help="Include this to remove the step operator from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-x",
    "--secrets_manager",
    "secrets_manager_flag",
    help="Include this to remove the secrets manager from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store_flag",
    help="Include this to remove the feature store from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer_flag",
    help="Include this to remove the model deployer from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker_flag",
    help="Include this to remove the experiment tracker from this stack.",
    is_flag=True,
    required=False,
)
def remove_stack_component(
    stack_name: Optional[str],
    container_registry_flag: Optional[bool] = False,
    step_operator_flag: Optional[bool] = False,
    secrets_manager_flag: Optional[bool] = False,
    feature_store_flag: Optional[bool] = False,
    model_deployer_flag: Optional[bool] = False,
    experiment_tracker_flag: Optional[bool] = False,
) -> None:
    """Remove stack components from a stack."""

    cli_utils.print_active_profile()

    repo = Repository()

    active_stack_name = repo.active_stack_name
    stack_name = stack_name or active_stack_name

    with console.status(f"Updating stack `{stack_name}`...\n"):
        repo = Repository()
        try:
            current_stack = repo.get_stack(stack_name)
        except KeyError:
            cli_utils.error(
                f"Stack `{stack_name}` cannot be updated as it does not exist.",
            )
        stack_components = current_stack.components

        if container_registry_flag:
            stack_components.pop(StackComponentType.CONTAINER_REGISTRY, None)

        if step_operator_flag:
            stack_components.pop(StackComponentType.STEP_OPERATOR, None)

        if secrets_manager_flag:
            stack_components.pop(StackComponentType.SECRETS_MANAGER, None)

        if feature_store_flag:
            stack_components.pop(StackComponentType.FEATURE_STORE, None)

        if model_deployer_flag:
            stack_components.pop(StackComponentType.MODEL_DEPLOYER, None)

        if experiment_tracker_flag:
            stack_components.pop(StackComponentType.EXPERIMENT_TRACKER, None)

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.update_stack(stack_name, stack_)
        cli_utils.declare(f"Stack `{stack_name}` successfully updated!")


@stack.command("rename")
@click.argument("current_stack_name", type=str, required=True)
@click.argument("new_stack_name", type=str, required=True)
def rename_stack(
    current_stack_name: str,
    new_stack_name: str,
) -> None:
    """Rename a stack."""
    with console.status(f"Renaming stack `{current_stack_name}`...\n"):
        repo = Repository()
        try:
            current_stack = repo.get_stack(current_stack_name)
        except KeyError:
            cli_utils.error(
                f"Stack `{current_stack_name}` cannot be renamed as it does "
                f"not exist.",
            )
        stack_components = current_stack.components

        try:
            repo.zen_store.get_stack(new_stack_name)
            cli_utils.error(
                f"Stack `{new_stack_name}` already exists. Please choose a "
                f"different name.",
            )
        except KeyError:
            pass

        new_stack_ = Stack.from_components(
            name=new_stack_name, components=stack_components
        )
        repo.update_stack(current_stack_name, new_stack_)
        cli_utils.declare(
            f"Stack `{current_stack_name}` successfully renamed as `{new_stack_name}`!"
        )


@stack.command("list")
def list_stacks() -> None:
    """List all available stacks in the active profile."""
    cli_utils.print_active_profile()

    repo = Repository()

    if len(repo.stack_configurations) == 0:
        cli_utils.error("No stacks registered!")

    active_stack_name = repo.active_stack_name

    stack_dicts = []
    for stack_name, stack_configuration in repo.stack_configurations.items():
        is_active = stack_name == active_stack_name
        stack_config = {
            "ACTIVE": ":point_right:" if is_active else "",
            "STACK NAME": stack_name,
            **{
                component_type.value.upper(): value
                for component_type, value in stack_configuration.items()
            },
        }
        stack_dicts.append(stack_config)

    cli_utils.print_table(stack_dicts)


@stack.command(
    "describe",
    help="Show details about the current active stack.",
)
@click.argument(
    "stack_name",
    type=click.STRING,
    required=False,
)
def describe_stack(stack_name: Optional[str]) -> None:
    """Show details about a named stack or the active stack."""
    cli_utils.print_active_profile()

    repo = Repository()

    stack_configurations = repo.stack_configurations
    if len(stack_configurations) == 0:
        cli_utils.error("No stacks registered.")

    active_stack_name = repo.active_stack_name
    stack_name = stack_name or active_stack_name
    if not stack_name:
        cli_utils.error(
            "Argument 'stack_name' was not provided and no stack is set as active."
        )

    try:
        stack_configuration = stack_configurations[stack_name]
    except KeyError:
        cli_utils.error(f"Stack '{stack_name}' does not exist.")

    cli_utils.print_stack_configuration(
        stack_configuration,
        active=stack_name == active_stack_name,
        stack_name=stack_name,
    )


@stack.command("delete")
@click.argument("stack_name", type=str)
@click.option("--yes", "-y", is_flag=True, required=False)
@click.option("--force", "-f", "old_force", is_flag=True, required=False)
def delete_stack(
    stack_name: str, yes: bool = False, old_force: bool = False
) -> None:
    """Delete a stack."""
    if old_force:
        yes = old_force
        cli_utils.warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or "
            "`-y` instead."
        )
    cli_utils.print_active_profile()
    confirmation = yes or cli_utils.confirmation(
        f"This will delete stack '{stack_name}' from your repository. \n"
        "Are you sure you want to proceed?"
    )

    if not confirmation:
        cli_utils.declare("Stack deletion canceled.")

    with console.status(f"Deleting stack '{stack_name}'...\n"):
        cfg = GlobalConfiguration()
        repo = Repository()

        if cfg.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted while it is globally "
                f"active. Please choose a different active global stack first "
                f"by running 'zenml stack set --global STACK'."
            )

        if repo.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted while it is "
                f"active. Please choose a different active stack first by "
                f"running 'zenml stack set STACK'."
            )

    Repository().deregister_stack(stack_name)
    cli_utils.declare(f"Deleted stack '{stack_name}'.")


@stack.command("set")
@click.argument("stack_name", type=str)
@click.option(
    "--global",
    "-g",
    "global_profile",
    is_flag=True,
    help="Set the active stack globally.",
)
def set_active_stack_command(
    stack_name: str, global_profile: bool = False
) -> None:
    """Sets a stack as active.

    If the '--global' flag is set, the global active stack will be set,
    otherwise the repository active stack takes precedence.
    """
    set_active_stack(stack_name, global_profile)


def set_active_stack(stack_name: str, global_profile: bool = False) -> None:
    """Sets a stack as active.

    If the '--global' flag is set, the global active stack will be set,
    otherwise the repository active stack takes precedence.

    Args:
        stack_name: Unique name of the stack
        global_profile: If the stack should be created on the global profile
    """
    cli_utils.print_active_profile()
    scope = " global" if global_profile else ""
    repo = Repository()
    with console.status(
        f"Setting the{scope} active stack to '{stack_name}'..."
    ):
        if global_profile:
            repo.active_profile.activate_stack(stack_name)
        else:
            repo.activate_stack(stack_name)

        cli_utils.declare(f"Active{scope} stack set to: '{stack_name}'")


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    cli_utils.print_active_profile()

    with console.status("Getting the active stack..."):
        repo = Repository()
        cli_utils.declare(f"The active stack is: '{repo.active_stack_name}'")


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the active stack."""
    cli_utils.print_active_profile()

    stack_ = Repository().active_stack
    cli_utils.declare(
        f"Provisioning resources for active stack '{stack_.name}'."
    )
    try:
        stack_.provision()
        stack_.resume()
    except ProvisioningError as e:
        cli_utils.error(str(e))


@stack.command("down")
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Deprovisions local resources instead of suspending "
    "them. Use `-y/--yes` instead.",
)
def down_stack(force: bool = False, old_force: bool = False) -> None:
    """Suspends resources of the active stack deployment."""
    if old_force:
        force = old_force
        cli_utils.warning(
            "The `--force` flag will soon be deprecated. Use `--yes` "
            "or `-y` instead."
        )
    cli_utils.print_active_profile()

    stack_ = Repository().active_stack

    if force:
        cli_utils.declare(
            f"Deprovisioning resources for active stack '{stack_.name}'."
        )
        stack_.deprovision()
    else:
        cli_utils.declare(
            f"Suspending resources for active stack '{stack_.name}'."
        )
        stack_.suspend()


def _get_component_as_dict(
    component_type: StackComponentType, component_name: str
) -> Dict[str, str]:
    """Return a dict represention of a component's key config values"""
    repo = Repository()
    component = repo.get_stack_component(component_type, name=component_name)
    component_dict = {
        key: value
        for key, value in json.loads(component.json()).items()
        if key != "uuid" and value is not None
    }
    component_dict["flavor"] = component.FLAVOR
    return component_dict


@stack.command("export")
@click.argument("stack_name", type=str, required=True)
@click.argument("filename", type=str, required=False)
def export_stack(stack_name: str, filename: Optional[str]) -> None:
    """Export a stack to YAML."""
    track_event(AnalyticsEvent.EXPORT_STACK)

    # Get configuration of given stack
    # TODO [ENG-893]: code duplicate with describe_stack()
    repo = Repository()

    stack_configurations = repo.stack_configurations
    if len(stack_configurations) == 0:
        cli_utils.error("No stacks registered.")

    try:
        stack_configuration = stack_configurations[stack_name]
    except KeyError:
        cli_utils.error(f"Stack '{stack_name}' does not exist.")

    # create a dict of all components in the specified stack
    component_data = {}
    for component_type, component_name in stack_configuration.items():
        component_dict = _get_component_as_dict(component_type, component_name)
        component_data[str(component_type)] = component_dict

    # write zenml version and stack dict to YAML
    yaml_data = {
        "zenml_version": zenml.__version__,
        "stack_name": stack_name,
        "components": component_data,
    }
    if filename is None:
        filename = stack_name + ".yaml"
    write_yaml(filename, yaml_data)
    cli_utils.declare(f"Exported stack '{stack_name}' to file '{filename}'.")


def _import_stack_component(
    component_type: StackComponentType, component_config: Dict[str, str]
) -> str:
    """import a single stack component with given type/config"""
    component_type = StackComponentType(component_type)
    component_name = component_config.pop("name")
    component_flavor = component_config.pop("flavor")

    # make sure component can be registered, otherwise ask for new name
    while True:
        # check if component already exists
        try:
            other_component = _get_component_as_dict(
                component_type, component_name
            )

        # component didn't exist yet, so we create it.
        except KeyError:
            break

        # check whether other component has exactly same config as export
        other_is_same = True
        for key, value in component_config.items():
            if key not in other_component or other_component[key] != value:
                other_is_same = False
                break

        # component already exists and is correctly configured -> done
        if other_is_same:
            return component_name

        # component already exists but with different config -> rename
        display_name = _component_display_name(component_type)
        component_name = click.prompt(
            f"A component of type '{display_name}' with the name "
            f"'{component_name}' already exists, "
            f"but is configured differently. "
            f"Please choose a different name.",
            type=str,
        )

    _register_stack_component(
        component_type=component_type,
        component_name=component_name,
        component_flavor=component_flavor,
        **component_config,
    )
    return component_name


@stack.command("import")
@click.argument("stack_name", type=str, required=True)
@click.argument("filename", type=str, required=False)
@click.pass_context
def import_stack(
    ctx: click.Context, stack_name: str, filename: Optional[str]
) -> None:
    """Import a stack from YAML."""
    track_event(AnalyticsEvent.IMPORT_STACK)

    # handle 'zenml stack import file.yaml' calls
    if stack_name.endswith(".yaml") and filename is None:
        filename = stack_name
        data = read_yaml(filename)
        stack_name = data["stack_name"]  # read stack_name from export

    # standard 'zenml stack import stack_name [file.yaml]' calls
    else:
        # if filename is not given, assume default export name
        # "<stack_name>.yaml"
        if filename is None:
            filename = stack_name + ".yaml"
        data = read_yaml(filename)
        cli_utils.declare(f"Using '{filename}' to import '{stack_name}' stack.")

    # assert zenml version is the same
    if data["zenml_version"] != zenml.__version__:
        cli_utils.error(
            f"Cannot import stacks from other ZenML versions. "
            f"The stack was created using ZenML version "
            f"{data['zenml_version']}, you have version "
            f"{zenml.__version__} installed."
        )

    # ask user for new stack_name if current one already exists
    repo = Repository()
    registered_stacks = {stack_.name for stack_ in repo.stacks}
    while stack_name in registered_stacks:
        stack_name = click.prompt(
            f"Stack `{stack_name}` already exists. "
            f"Please choose a different name.",
            type=str,
        )

    # import stack components
    component_names = {}
    for component_type, component_config in data["components"].items():
        component_name = _import_stack_component(
            component_type=component_type,
            component_config=component_config,
        )
        component_names[component_type + "_name"] = component_name

    # register new stack
    ctx.invoke(register_stack, stack_name=stack_name, **component_names)
