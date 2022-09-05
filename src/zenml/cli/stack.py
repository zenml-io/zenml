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

import getpass
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
from zenml.exceptions import ProvisioningError, StackValidationError
from zenml.repository import Repository
from zenml.secret import ArbitrarySecretSchema
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


@stack.command(
    "register",
    context_settings=dict(ignore_unknown_options=True),
    help="Register a stack with components.",
)
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
    "-an",
    "--annotator",
    "annotator_name",
    help="Name of the annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator_name",
    help="Name of the data validator for this stack.",
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
@click.option(
    "--decouple_stores",
    "decouple_stores",
    is_flag=True,
    help="Decouple the given artifact/metadata store from prior associations.",
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
    annotator_name: Optional[str] = None,
    data_validator_name: Optional[str] = None,
    set_stack: bool = False,
    decouple_stores: bool = False,
) -> None:
    """Register a stack.

    Args:
        stack_name: Unique name of the stack
        metadata_store_name: Name of the metadata store for this stack.
        artifact_store_name: Name of the artifact store for this stack.
        orchestrator_name: Name of the orchestrator for this stack.
        container_registry_name: Name of the container registry for this stack.
        secrets_manager_name: Name of the secrets manager for this stack.
        step_operator_name: Name of the step operator for this stack.
        feature_store_name: Name of the feature store for this stack.
        model_deployer_name: Name of the model deployer for this stack.
        experiment_tracker_name: Name of the experiment tracker for this stack.
        alerter_name: Name of the alerter for this stack.
        annotator_name: Name of the annotator for this stack.
        data_validator_name: Name of the data validator for this stack.
        set_stack: Immediately set this stack as active.
        decouple_stores: Resets the previous couplings of the given
            artifact/metadata stores and creates a new one.
    """
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

        if annotator_name:
            stack_components[
                StackComponentType.ANNOTATOR
            ] = repo.get_stack_component(
                StackComponentType.ANNOTATOR,
                name=annotator_name,
            )

        if data_validator_name:
            stack_components[
                StackComponentType.DATA_VALIDATOR
            ] = repo.get_stack_component(
                StackComponentType.DATA_VALIDATOR,
                name=data_validator_name,
            )

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        try:
            repo.register_stack(stack_, decouple_stores=decouple_stores)
        except StackValidationError as e:
            cli_utils.error(e)  # type: ignore[arg-type]

        cli_utils.declare(f"Stack '{stack_name}' successfully registered!")

    if set_stack:
        set_active_stack(stack_name=stack_name)


@stack.command(
    "update",
    context_settings=dict(ignore_unknown_options=True),
    help="Update a stack with new components.",
)
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
@click.option(
    "-an",
    "--annotator",
    "annotator_name",
    help="Name of the new annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator_name",
    help="Name of the data validator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "--decouple_stores",
    "decouple_stores",
    is_flag=True,
    help="Decouple the given artifact/metadata store from prior associations.",
    type=click.BOOL,
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
    annotator_name: Optional[str] = None,
    data_validator_name: Optional[str] = None,
    decouple_stores: bool = False,
) -> None:
    """Update a stack.

    Args:
        stack_name: Name of the stack to update.
        metadata_store_name: Name of the new metadata store for this stack.
        artifact_store_name: Name of the new artifact store for this stack.
        orchestrator_name: Name of the new orchestrator for this stack.
        container_registry_name: Name of the new container registry for this
            stack.
        step_operator_name: Name of the new step operator for this stack.
        secrets_manager_name: Name of the new secrets manager for this
            stack.
        feature_store_name: Name of the new feature store for this stack.
        model_deployer_name: Name of the new model deployer for this stack.
        experiment_tracker_name: Name of the new experiment tracker for this
            stack.
        alerter_name: Name of the new alerter for this stack.
        annotator_name: Name of the new annotator for this stack.
        data_validator_name: Name of the new data validator for this stack.
        decouple_stores: Resets the previous couplings of the given
            artifact/metadata stores and creates a new one.
    """
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

        if annotator_name:
            stack_components[
                StackComponentType.ANNOTATOR
            ] = repo.get_stack_component(
                StackComponentType.ANNOTATOR,
                name=annotator_name,
            )

        if data_validator_name:
            stack_components[
                StackComponentType.DATA_VALIDATOR
            ] = repo.get_stack_component(
                StackComponentType.DATA_VALIDATOR,
                name=data_validator_name,
            )

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        try:
            repo.update_stack(
                name=stack_name,
                stack=stack_,
                decouple_stores=decouple_stores,
            )
        except StackValidationError as e:
            cli_utils.error(e)  # type: ignore[arg-type]

        cli_utils.declare(f"Stack `{stack_name}` successfully updated!")


@stack.command(
    "remove-component",
    context_settings=dict(ignore_unknown_options=True),
    help="Remove stack components from a stack.",
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
@click.option(
    "-al",
    "--alerter",
    "alerter_flag",
    help="Include this to remove the alerter from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator_flag",
    help="Include this to remove the annotator from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator_flag",
    help="Include this to remove the data validator from this stack.",
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
    alerter_flag: Optional[bool] = False,
    annotator_flag: Optional[bool] = False,
    data_validator_flag: Optional[bool] = False,
) -> None:
    """Remove stack components from a stack.

    Args:
        stack_name: Name of the stack to remove components from.
        container_registry_flag: To remove the container registry from this stack.
        step_operator_flag: To remove the step operator from this stack.
        secrets_manager_flag: To remove the secrets manager from this stack.
        feature_store_flag: To remove the feature store from this stack.
        model_deployer_flag: To remove the model deployer from this stack.
        experiment_tracker_flag: To remove the experiment tracker from this
            stack.
        alerter_flag: To remove the alerter from this stack.
        annotator_flag: To remove the annotator from this stack.
        data_validator_flag: To remove the data validator from this stack.
    """
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

        if alerter_flag:
            stack_components.pop(StackComponentType.ALERTER, None)

        if annotator_flag:
            stack_components.pop(StackComponentType.ANNOTATOR, None)

        if data_validator_flag:
            stack_components.pop(StackComponentType.DATA_VALIDATOR, None)

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.update_stack(stack_name, stack_)
        cli_utils.declare(f"Stack `{stack_name}` successfully updated!")


@stack.command("rename", help="Rename a stack.")
@click.argument("current_stack_name", type=str, required=True)
@click.argument("new_stack_name", type=str, required=True)
def rename_stack(
    current_stack_name: str,
    new_stack_name: str,
) -> None:
    """Rename a stack.

    Args:
        current_stack_name: Name of the stack to rename.
        new_stack_name: New name of the stack.
    """
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
    """Show details about a named stack or the active stack.

    Args:
        stack_name: Name of the stack to describe.
    """
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


@stack.command("delete", help="Delete a stack given its name.")
@click.argument("stack_name", type=str)
@click.option("--yes", "-y", is_flag=True, required=False)
@click.option("--force", "-f", "old_force", is_flag=True, required=False)
def delete_stack(
    stack_name: str, yes: bool = False, old_force: bool = False
) -> None:
    """Delete a stack.

    Args:
        stack_name: Name of the stack to delete.
        yes: Stack will be deleted without prompting for
            confirmation.
        old_force: Stack will be deleted without prompting for
            confirmation.
    """
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


@stack.command("set", help="Sets a stack as active.")
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

    Args:
        stack_name: Name of the stack to set as active.
        global_profile: Set the active stack globally.
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


@stack.command(
    "down", help="Suspends resources of the active stack deployment."
)
@click.option(
    "--yes",
    "-y",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Deprovisions local resources instead of suspending "
    "them. Use `-f/--force` instead.",
)
@click.option(
    "--force",
    "-f",
    "force",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_stack(force: bool = False, old_force: bool = False) -> None:
    """Suspends resources of the active stack deployment.

    Args:
        force: Deprovisions local resources instead of suspending them.
        old_force: DEPRECATED: Deprovisions local resources instead of
            suspending them. Use `-f/--force` instead.
    """
    if old_force:
        force = old_force
        cli_utils.warning(
            "The `--yes` flag will soon be deprecated. Use `--force` "
            "or `-f` instead."
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
    """Return a dict representation of a component's key config values.

    Args:
        component_type: The type of component to get.
        component_name: The name of the component to get.

    Returns:
        A dict representation of the component's key config values.
    """
    repo = Repository()
    component = repo.get_stack_component(component_type, name=component_name)
    component_dict = {
        key: value
        for key, value in json.loads(component.json()).items()
        if key != "uuid" and value is not None
    }
    component_dict["flavor"] = component.FLAVOR
    return component_dict


@stack.command("export", help="Exports a stack to a YAML file.")
@click.argument("stack_name", type=str, required=True)
@click.argument("filename", type=str, required=False)
def export_stack(stack_name: str, filename: Optional[str]) -> None:
    """Export a stack to YAML.

    Args:
        stack_name: The name of the stack to export.
        filename: The filename to export the stack to.
    """
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
    """Import a single stack component with given type/config.

    Args:
        component_type: The type of component to import.
        component_config: The config of the component to import.

    Returns:
        The name of the imported component.
    """
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


@stack.command("import", help="Import a stack from YAML.")
@click.argument("stack_name", type=str, required=True)
@click.argument("filename", type=str, required=False)
@click.option(
    "--ignore-version-mismatch",
    is_flag=True,
    help="Import stack components even if the installed version of ZenML "
    "is different from the one specified in the stack YAML file",
)
@click.option(
    "--decouple_stores",
    "decouple_stores",
    is_flag=True,
    help="Decouple the given artifact/metadata store from prior associations.",
    type=click.BOOL,
)
@click.pass_context
def import_stack(
    ctx: click.Context,
    stack_name: str,
    filename: Optional[str],
    ignore_version_mismatch: bool = False,
    decouple_stores: bool = False,
) -> None:
    """Import a stack from YAML.

    Args:
        ctx: The click context.
        stack_name: The name of the stack to import.
        filename: The filename to import the stack from.
        ignore_version_mismatch: Import stack components even if
            the installed version of ZenML is different from the
            one specified in the stack YAML file.
        decouple_stores: Resets the previous couplings of the given
            artifact/metadata stores and creates a new one.
    """
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

    # assert zenml version is the same if force is false
    if data["zenml_version"] != zenml.__version__:
        if ignore_version_mismatch:
            cli_utils.warning(
                f"The stack that will be installed is using ZenML version "
                f"{data['zenml_version']}. You have version "
                f"{zenml.__version__} installed. Some components might not "
                "work as expected."
            )
        else:
            cli_utils.error(
                f"Cannot import stacks from other ZenML versions. "
                f"The stack was created using ZenML version "
                f"{data['zenml_version']}, you have version "
                f"{zenml.__version__} installed. You can "
                "retry using the `--ignore-version-mismatch` "
                "flag. However, be aware that this might "
                "fail or lead to other unexpected behavior."
            )

    # ask user for new stack_name if current one already exists
    repo = Repository()
    while stack_name in repo.stack_configurations:
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
    ctx.invoke(
        register_stack,
        stack_name=stack_name,
        decouple_stores=decouple_stores,
        **component_names,
    )


@stack.command("copy", help="Copy a stack to a new stack name.")
@click.argument("source_stack", type=str, required=True)
@click.argument("target_stack", type=str, required=True)
@click.option(
    "--from",
    "source_profile_name",
    type=str,
    required=False,
    help="The profile from which to copy the stack.",
)
@click.option(
    "--to",
    "target_profile_name",
    type=str,
    required=False,
    help="The profile to which to copy the stack.",
)
def copy_stack(
    source_stack: str,
    target_stack: str,
    source_profile_name: Optional[str] = None,
    target_profile_name: Optional[str] = None,
) -> None:
    """Copy a stack.

    Args:
        source_stack: The name of the stack to copy.
        target_stack: Name of the copied stack.
        source_profile_name: Name of the profile from which to copy.
        target_profile_name: Name of the profile to which to copy.
    """
    track_event(AnalyticsEvent.COPIED_STACK)

    if source_profile_name:
        try:
            source_profile = GlobalConfiguration().profiles[source_profile_name]
        except KeyError:
            cli_utils.error(
                f"Unable to find source profile '{source_profile_name}'."
            )
    else:
        source_profile = Repository().active_profile

    if target_profile_name:
        try:
            target_profile = GlobalConfiguration().profiles[target_profile_name]
        except KeyError:
            cli_utils.error(
                f"Unable to find target profile '{target_profile_name}'."
            )
    else:
        target_profile = Repository().active_profile

    # Use different repositories for fetching/registering the stack depending
    # on the source/target profile
    source_repo = Repository(profile=source_profile)
    target_repo = Repository(profile=target_profile)

    with console.status(f"Copying stack `{source_stack}`...\n"):
        try:
            stack_wrapper = source_repo.zen_store.get_stack(source_stack)
        except KeyError:
            cli_utils.error(
                f"Stack `{source_stack}` cannot be copied as it does not exist."
            )

        if target_stack in target_repo.stack_configurations:
            cli_utils.error(
                f"Can't copy stack as a stack with the name '{target_stack}' "
                "already exists."
            )
        stack_wrapper.name = target_stack
        target_repo.zen_store.register_stack(stack_wrapper)


@stack.command(
    "register-secrets",
    help="Interactively register all required secrets for a stack.",
)
@click.argument("stack_name", type=str, required=False)
@click.option(
    "--skip-existing",
    "skip_existing",
    is_flag=True,
    default=False,
    help="Skip secrets with existing values.",
    type=bool,
)
def register_secrets(
    skip_existing: bool,
    stack_name: Optional[str] = None,
) -> None:
    """Interactively registers all required secrets for a stack.

    Args:
        skip_existing: If `True`, skip asking for secret values that already
            exist.
        stack_name: Name of the stack for which to register secrets. If empty,
            the active stack will be used.
    """
    cli_utils.print_active_profile()

    if stack_name:
        try:
            stack_ = Repository().get_stack(stack_name)
        except KeyError:
            cli_utils.error(f"No stack found for name `{stack_name}`.")
    else:
        stack_ = Repository().active_stack
        cli_utils.declare(
            f"No stack name specified, using the active stack `{stack_.name}`."
        )

    required_secrets = stack_.required_secrets
    if not required_secrets:
        cli_utils.declare("No secrets required for this stack.")
        return

    secret_names = {s.name for s in required_secrets}
    secrets_manager = stack_.secrets_manager
    if not secrets_manager:
        cli_utils.error(
            f"Unable to register required secrets ({secret_names}) because "
            "the stack doesn't contain a secrets manager. Please add a secrets "
            "manager to your stack and then rerun this command."
        )

    secrets_to_register = []
    secrets_to_update = []
    for name in secret_names:
        try:
            secret_content = secrets_manager.get_secret(name).content.copy()
            secret_exists = True
        except KeyError:
            secret_content = {}
            secret_exists = False

        required_keys = {s.key for s in required_secrets if s.name == name}
        needs_update = False

        for key in required_keys:
            existing_value = secret_content.get(key, None)

            if existing_value:
                if skip_existing:
                    continue

                value = getpass.getpass(
                    f"Value for secret `{name}.{key}` "
                    "(Leave empty to use existing value):"
                )
                if value:
                    value = cli_utils.expand_argument_value_from_file(
                        name=key, value=value
                    )
                else:
                    value = existing_value

                # only need to update if the value changed
                needs_update = needs_update or value != existing_value
            else:
                value = None
                while not value:
                    value = getpass.getpass(f"Value for secret `{name}.{key}`:")
                value = cli_utils.expand_argument_value_from_file(
                    name=key, value=value
                )
                needs_update = True

            secret_content[key] = value

        secret = ArbitrarySecretSchema(name=name, **secret_content)

        if not secret_exists:
            secrets_to_register.append(secret)
        elif needs_update:
            secrets_to_update.append(secret)

    for secret in secrets_to_register:
        cli_utils.declare(f"Registering secret `{secret.name}`:")
        cli_utils.pretty_print_secret(secret=secret, hide_secret=True)
        secrets_manager.register_secret(secret)
    for secret in secrets_to_update:
        cli_utils.declare(f"Updating secret `{secret.name}`:")
        cli_utils.pretty_print_secret(secret=secret, hide_secret=True)
        secrets_manager.update_secret(secret)
