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

from typing import Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import StackComponentType
from zenml.exceptions import ProvisioningError
from zenml.repository import Repository
from zenml.stack import Stack


# Stacks
@cli.group()
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

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.register_stack(stack_)
        cli_utils.declare(f"Stack '{stack_name}' successfully registered!")


@stack.command("update", context_settings=dict(ignore_unknown_options=True))
@click.argument("stack_name", type=str, required=True)
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
    "--model-deployer",
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
def update_stack(
    stack_name: str,
    metadata_store_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
    orchestrator_name: Optional[str] = None,
    container_registry_name: Optional[str] = None,
    step_operator_name: Optional[str] = None,
    secrets_manager_name: Optional[str] = None,
    feature_store_name: Optional[str] = None,
    model_deployer_name: Optional[str] = None,
    experiment_tracker_name: Optional[str] = None,
) -> None:
    """Update a stack."""
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

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.update_stack(stack_name, stack_)
        cli_utils.declare(f"Stack `{stack_name}` successfully updated!")


@stack.command(
    "remove-component", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("stack_name", type=str, required=True)
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
    stack_name: str,
    container_registry_flag: Optional[bool] = False,
    step_operator_flag: Optional[bool] = False,
    secrets_manager_flag: Optional[bool] = False,
    feature_store_flag: Optional[bool] = False,
    model_deployer_flag: Optional[bool] = False,
    experiment_tracker_flag: Optional[bool] = False,
) -> None:
    """Remove stack components from a stack."""
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
                f"Stack `{current_stack_name}` cannot be renamed as it does not exist.",
            )
        stack_components = current_stack.components

        registered_stacks = {stack.name for stack in repo.stacks}
        if new_stack_name in registered_stacks:
            cli_utils.error(
                f"Stack `{new_stack_name}` already exists. Please choose a different name.",
            )
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
        cli_utils.warning("No stacks registered!")
        return

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

    active_stack_name = repo.active_stack_name
    stack_name = stack_name or active_stack_name

    if not stack_name:
        cli_utils.warning("No stack is set as active!")
        return

    stack_configurations = repo.stack_configurations
    if len(stack_configurations) == 0:
        cli_utils.warning("No stacks registered!")
        return

    try:
        stack_configuration = stack_configurations[stack_name]
    except KeyError:
        cli_utils.error(f"Stack '{stack_name}' does not exist.")
        return

    cli_utils.print_stack_configuration(
        stack_configuration,
        active=stack_name == active_stack_name,
        stack_name=stack_name,
    )


@stack.command("delete")
@click.argument("stack_name", type=str)
def delete_stack(stack_name: str) -> None:
    """Delete a stack."""
    cli_utils.print_active_profile()

    with console.status(f"Deleting stack '{stack_name}'...\n"):
        cfg = GlobalConfiguration()
        repo = Repository()

        if cfg.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted while it is globally "
                f"active. Please choose a different active global stack first "
                f"by running 'zenml stack set --global STACK'."
            )
            return

        if repo.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted while it is "
                f"active. Please choose a different active stack first by "
                f"running 'zenml stack set STACK'."
            )
            return

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
def set_active_stack(stack_name: str, global_profile: bool = False) -> None:
    """Sets a stack as active.

    If the '--global' flag is set, the global active stack will be set,
    otherwise the repository active stack takes precedence.
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
    "--force",
    "-f",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_stack(force: bool = False) -> None:
    """Suspends resources of the active stack deployment."""
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
