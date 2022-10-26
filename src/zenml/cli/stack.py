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
from uuid import UUID

import click

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import _component_display_name, print_stacks_table
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import ProvisioningError
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
    "--share",
    "share",
    is_flag=True,
    help="Use this flag to share this stack with other users.",
    type=click.BOOL,
)
def register_stack(
    stack_name: str,
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
    share: bool = False,
) -> None:
    """Register a stack.

    Args:
        stack_name: Unique name of the stack
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
        share: Share the stack with other users.
    """
    cli_utils.print_active_config()

    with console.status(f"Registering stack '{stack_name}'...\n"):
        client = Client()

        type_component_mapping: Dict[StackComponentType, Optional[str]] = {
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ALERTER: alerter_name,
            StackComponentType.ANNOTATOR: annotator_name,
            StackComponentType.CONTAINER_REGISTRY: container_registry_name,
            StackComponentType.DATA_VALIDATOR: data_validator_name,
            StackComponentType.EXPERIMENT_TRACKER: experiment_tracker_name,
            StackComponentType.FEATURE_STORE: feature_store_name,
            StackComponentType.MODEL_DEPLOYER: model_deployer_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
            StackComponentType.SECRETS_MANAGER: secrets_manager_name,
            StackComponentType.STEP_OPERATOR: step_operator_name,
        }
        stack_components = dict()

        for c_type, name in type_component_mapping.items():
            if name:
                stack_components[c_type] = [
                    cli_utils.get_component_by_id_or_name_or_prefix(
                        client=client,
                        component_type=c_type,
                        id_or_name_or_prefix=name,
                    ).id
                ]

        # click<8.0.0 gives flags a default of None
        if share is None:
            share = False

        from zenml.models import StackModel

        stack_ = StackModel(
            name=stack_name,
            components=stack_components,
            is_shared=share,
            project=client.active_project.id,
            user=client.active_user.id,
        )

        created_stack = client.register_stack(stack_)
        cli_utils.declare(f"Stack '{stack_name}' successfully registered!")

    if set_stack:
        client.activate_stack(stack=created_stack)


@stack.command(
    "update",
    context_settings=dict(ignore_unknown_options=True),
    help="Update a stack with new components.",
)
@click.argument("stack_name_or_id", type=str, required=False)
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
def update_stack(
    stack_name_or_id: Optional[str],
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
) -> None:
    """Update a stack.

    Args:
        stack_name_or_id: Name or id of the stack to update.
        artifact_store_name: Name of the new artifact store for this stack.
        orchestrator_name: Name of the new orchestrator for this stack.
        container_registry_name: Name of the new container registry for this
            stack.
        step_operator_name: Name of the new step operator for this stack.
        secrets_manager_name: Name of the new secrets manager for this stack.
        feature_store_name: Name of the new feature store for this stack.
        model_deployer_name: Name of the new model deployer for this stack.
        experiment_tracker_name: Name of the new experiment tracker for this
            stack.
        alerter_name: Name of the new alerter for this stack.
        annotator_name: Name of the new annotator for this stack.
        data_validator_name: Name of the new data validator for this stack.
    """
    cli_utils.print_active_config()

    client = Client()

    active_stack_name = client.active_stack_model.name
    stack_name_or_id = stack_name_or_id or active_stack_name

    with console.status(f"Updating stack `{stack_name_or_id}`...\n"):
        client = Client()
        try:
            stack_to_update = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=stack_name_or_id
            )
        except KeyError:
            cli_utils.error(
                f"Stack `{stack_name_or_id}` cannot be updated as it does not"
                f" exist.",
            )

        type_component_mapping: Dict[StackComponentType, Optional[str]] = {
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ALERTER: alerter_name,
            StackComponentType.ANNOTATOR: annotator_name,
            StackComponentType.CONTAINER_REGISTRY: container_registry_name,
            StackComponentType.DATA_VALIDATOR: data_validator_name,
            StackComponentType.EXPERIMENT_TRACKER: experiment_tracker_name,
            StackComponentType.FEATURE_STORE: feature_store_name,
            StackComponentType.MODEL_DEPLOYER: model_deployer_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
            StackComponentType.SECRETS_MANAGER: secrets_manager_name,
            StackComponentType.STEP_OPERATOR: step_operator_name,
        }

        stack_components = stack_to_update.components

        for c_type, name in type_component_mapping.items():
            if name:
                stack_components[c_type] = [
                    cli_utils.get_component_by_id_or_name_or_prefix(
                        client=client,
                        component_type=c_type,
                        id_or_name_or_prefix=name,
                    ).id
                ]

        stack_to_update.components = stack_components

        client.update_stack(stack_to_update)
        cli_utils.declare(
            f"Stack `{stack_to_update.name}` successfully " f"updated!"
        )


@stack.command(
    "share",
    context_settings=dict(ignore_unknown_options=True),
    help="Share a stack and all its components.",
)
@click.argument("stack_name_or_id", type=str, required=False)
def share_stack(
    stack_name_or_id: Optional[str],
) -> None:
    """Share a stack with your team.

    Args:
        stack_name_or_id: Name or id of the stack to share.
    """
    cli_utils.print_active_config()

    client = Client()

    active_stack_name = client.active_stack_model.name
    stack_name_or_id = stack_name_or_id or active_stack_name

    client = Client()
    try:
        stack_to_share = cli_utils.get_stack_by_id_or_name_or_prefix(
            client=client, id_or_name_or_prefix=stack_name_or_id
        )
    except KeyError:
        cli_utils.error(
            f"Stack `{stack_name_or_id}` cannot be updated as it does not "
            f"exist.",
        )
    else:
        for c_t, c in stack_to_share.to_hydrated_model().components.items():
            only_component = c[0]  # For future compatibility
            # with console.status(
            #     f"Sharing component `{only_component.name}`" f"...\n"
            # ):
            cli_utils.declare(
                f"A Stack can only be shared when all its "
                f"components are also shared. Component "
                f"'{only_component.name}' is also set to "
                f"shared."
            )

            only_component.is_shared = True
            client.update_stack_component(component=only_component)

        with console.status(f"Sharing stack `{stack_to_share.name}` ...\n"):

            stack_to_share.is_shared = True

            client.update_stack(stack_to_share)
            cli_utils.declare(
                f"Stack `{stack_to_share.name}` successfully shared!"
            )


@stack.command(
    "remove-component",
    context_settings=dict(ignore_unknown_options=True),
    help="Remove stack components from a stack.",
)
@click.argument("stack_name_or_id", type=str, required=False)
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
    stack_name_or_id: Optional[str],
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
        stack_name_or_id: Name of the stack to remove components from.
        container_registry_flag: To remove the container registry from this
            stack.
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
    cli_utils.print_active_config()

    client = Client()

    stack_name_or_id = stack_name_or_id or client.active_stack_model.name

    with console.status(f"Updating stack `{stack_name_or_id}`...\n"):
        client = Client()
        try:
            stack_to_update = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=stack_name_or_id
            )
        except KeyError:
            cli_utils.error(
                f"Stack `{stack_name_or_id}` cannot be updated as it does not "
                f"exist.",
            )

        if container_registry_flag:
            stack_to_update.components.pop(
                StackComponentType.CONTAINER_REGISTRY, None
            )

        if step_operator_flag:
            stack_to_update.components.pop(
                StackComponentType.STEP_OPERATOR, None
            )

        if secrets_manager_flag:
            stack_to_update.components.pop(
                StackComponentType.SECRETS_MANAGER, None
            )

        if feature_store_flag:
            stack_to_update.components.pop(
                StackComponentType.FEATURE_STORE, None
            )

        if model_deployer_flag:
            stack_to_update.components.pop(
                StackComponentType.MODEL_DEPLOYER, None
            )

        if experiment_tracker_flag:
            stack_to_update.components.pop(
                StackComponentType.EXPERIMENT_TRACKER, None
            )

        if alerter_flag:
            stack_to_update.components.pop(StackComponentType.ALERTER, None)

        if annotator_flag:
            stack_to_update.components.pop(StackComponentType.ANNOTATOR, None)

        if data_validator_flag:
            stack_to_update.components.pop(
                StackComponentType.DATA_VALIDATOR, None
            )

        client.update_stack(stack_to_update)
        cli_utils.declare(f"Stack `{stack_name_or_id}` successfully updated!")


@stack.command("rename", help="Rename a stack.")
@click.argument("current_stack_name_or_id", type=str, required=True)
@click.argument("new_stack_name", type=str, required=True)
def rename_stack(
    current_stack_name_or_id: str,
    new_stack_name: str,
) -> None:
    """Rename a stack.

    Args:
        current_stack_name_or_id: Name of the stack to rename.
        new_stack_name: New name of the stack.
    """
    with console.status(f"Renaming stack `{current_stack_name_or_id}`...\n"):
        client = Client()
        try:
            stack_to_rename = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=current_stack_name_or_id
            )
        except KeyError:
            cli_utils.error(
                f"Stack `{current_stack_name_or_id}` cannot be renamed as it "
                f"does not exist.",
            )

        try:
            cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=new_stack_name
            )
            cli_utils.error(
                f"Stack `{new_stack_name}` already exists. Please choose a "
                f"different name.",
            )
        except KeyError:
            pass

        stack_to_rename.name = new_stack_name
        client.update_stack(stack_to_rename)
        cli_utils.declare(
            f"Stack `{current_stack_name_or_id}` successfully renamed to `"
            f"{new_stack_name}`!"
        )


@stack.command("list")
@click.option("--just-mine", "-m", is_flag=True, required=False)
def list_stacks(just_mine: bool = False) -> None:
    """List all available stacks.

    Args:
        just_mine: To list only the stacks that the current user has created.
    """
    cli_utils.print_active_config()

    client = Client()
    stacks = client.stacks
    if just_mine:
        stacks = [
            stack for stack in stacks if stack.user.id == client.active_user.id
        ]
    print_stacks_table(client, stacks)


@stack.command(
    "describe",
    help="Show details about the current active stack.",
)
@click.argument(
    "stack_name_or_id",
    type=click.STRING,
    required=False,
)
def describe_stack(stack_name_or_id: Optional[str]) -> None:
    """Show details about a named stack or the active stack.

    Args:
        stack_name_or_id: Name of the stack to describe.
    """
    cli_utils.print_active_config()

    client = Client()
    active_stack = client.active_stack_model

    if stack_name_or_id:
        stack_to_describe = cli_utils.get_stack_by_id_or_name_or_prefix(
            client=client, id_or_name_or_prefix=stack_name_or_id
        ).to_hydrated_model()
    else:
        stack_to_describe = active_stack

    cli_utils.print_stack_configuration(
        stack_to_describe,
        active=stack_to_describe.id == active_stack.id,
    )


@stack.command("delete", help="Delete a stack given its name.")
@click.argument("stack_name_or_id", type=str)
@click.option("--yes", "-y", is_flag=True, required=False)
@click.option("--force", "-f", "old_force", is_flag=True, required=False)
def delete_stack(
    stack_name_or_id: str, yes: bool = False, old_force: bool = False
) -> None:
    """Delete a stack.

    Args:
        stack_name_or_id: Name or id of the stack to delete.
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
    cli_utils.print_active_config()
    confirmation = yes or cli_utils.confirmation(
        f"This will delete stack '{stack_name_or_id}'. \n"
        "Are you sure you want to proceed?"
    )

    if not confirmation:
        cli_utils.declare("Stack deletion canceled.")
        return

    with console.status(f"Deleting stack '{stack_name_or_id}'...\n"):
        cfg = GlobalConfiguration()
        client = Client()
        stack_to_delete = cli_utils.get_stack_by_id_or_name_or_prefix(
            client=client, id_or_name_or_prefix=stack_name_or_id
        )

        if cfg.active_stack_id is not None:
            global_active_stack = client.zen_store.get_stack(
                cfg.active_stack_id
            )
            if global_active_stack.name == stack_name_or_id:
                cli_utils.error(
                    f"Stack {stack_to_delete.name} cannot be deleted while it "
                    f"is globally active. Please choose a different active "
                    f"global stack first by running 'zenml stack set --global "
                    f"STACK'."
                )

        if client.active_stack_model.name == stack_to_delete.name:
            cli_utils.error(
                f"Stack {stack_to_delete.name} cannot be deleted while it is "
                f"active. Please choose a different active stack first by "
                f"running 'zenml stack set STACK'."
            )

    Client().deregister_stack(stack_to_delete)
    cli_utils.declare(f"Deleted stack '{stack_to_delete.name}'.")


@stack.command("set", help="Sets a stack as active.")
@click.argument("stack_name_or_id", type=str)
def set_active_stack_command(stack_name_or_id: str) -> None:
    """Sets a stack as active.

    Args:
        stack_name_or_id: Name of the stack to set as active.
    """
    cli_utils.print_active_config()
    scope = " repository" if Client().root else " global"
    client = Client()

    try:
        stack_to_set_active = cli_utils.get_stack_by_id_or_name_or_prefix(
            client=client, id_or_name_or_prefix=stack_name_or_id
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        with console.status(
            f"Setting the{scope} active stack to "
            f"'{stack_to_set_active.name}'..."
        ):
            client.activate_stack(stack_to_set_active)
            cli_utils.declare(
                f"Active{scope} stack set to: " f"'{stack_to_set_active.name}'"
            )


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    cli_utils.print_active_config()

    scope = " repository" if Client().uses_local_configuration else " global"

    with console.status("Getting the active stack..."):
        client = Client()
        cli_utils.declare(
            f"The{scope} active stack is: '{client.active_stack_model.name}'"
        )


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the active stack."""
    cli_utils.print_active_config()

    # TODO[Server]: Make this call a function in repo
    stack_ = Client().active_stack
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
    cli_utils.print_active_config()

    # TODO[Server]: Make this call a function in repo
    stack_ = Client().active_stack

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
    component_type: StackComponentType, component_name_or_id: str
) -> Dict[str, str]:
    """Return a dict representation of a component's key config values.

    Args:
        component_type: The type of component to get.
        component_name_or_id: The name of the component to get.

    Returns:
        A dict representation of the component's key config values.
    """
    client = Client()
    component = cli_utils.get_component_by_id_or_name_or_prefix(
        client=client,
        component_type=component_type,
        id_or_name_or_prefix=component_name_or_id,
    )
    component_dict = {
        key: value
        for key, value in json.loads(component.json()).items()
        if key != "uuid" and value is not None
    }
    component_dict["flavor"] = component.flavor
    return component_dict


@stack.command("export", help="Exports a stack to a YAML file.")
@click.argument("stack_name_or_id", type=str, required=False)
@click.argument("filename", type=str, required=False)
def export_stack(
    stack_name_or_id: Optional[str], filename: Optional[str]
) -> None:
    """Export a stack to YAML.

    Args:
        stack_name_or_id: The name of the stack to export.
        filename: The filename to export the stack to.
    """
    track_event(AnalyticsEvent.EXPORT_STACK)

    # Get configuration of given stack
    # TODO [ENG-893]: code duplicate with describe_stack()
    client = Client()
    active_stack = client.active_stack_model

    if stack_name_or_id:
        try:
            stack_to_export = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=stack_name_or_id
            ).to_hydrated_model()
        except KeyError:
            cli_utils.error(f"Stack '{stack_name_or_id}' does not exist.")
    else:
        stack_to_export = active_stack

    # write zenml version and stack dict to YAML
    yaml_data = stack_to_export.to_yaml()
    yaml_data["zenml_version"] = zenml.__version__

    if filename is None:
        filename = stack_to_export.name + ".yaml"
    write_yaml(filename, yaml_data)
    cli_utils.declare(
        f"Exported stack '{stack_to_export.name}' to file '{filename}'."
    )


def _import_stack_component(
    component_type: StackComponentType, component_config: Dict[str, str]
) -> UUID:
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
    component_id = component_config.pop("id")

    # make sure component can be registered, otherwise ask for new name
    client = Client()
    try:
        other_component = client.zen_store.get_stack_component(
            component_id=UUID(component_id)
        )
    except KeyError:
        pass
    else:
        return other_component.id

    try:
        component = cli_utils.get_stack_by_id_or_name_or_prefix(
            client=client, id_or_name_or_prefix=component_name
        )
        if component:
            # component with same name
            display_name = _component_display_name(component_type)
            component_name = click.prompt(
                f"A component of type '{display_name}' with the name "
                f"'{component_name}' already exists, "
                f"but is configured differently. "
                f"Please choose a different name.",
                type=str,
            )
    except click.ClickException:
        # component with same name
        display_name = _component_display_name(component_type)
        component_name = click.prompt(
            f"A component of type '{display_name}' with the name "
            f"'{component_name}' already exists, "
            f"but is configured differently. "
            f"Please choose a different name.",
            type=str,
        )
    except KeyError:
        pass

    from zenml.models import ComponentModel

    registered_component = client.register_stack_component(
        ComponentModel(
            user=client.active_user.id,
            project=client.active_project.id,
            type=component_type,
            name=component_name,
            flavor=component_flavor,
            configuration=component_config["configuration"],
        )
    )
    return registered_component.id


@stack.command("import", help="Import a stack from YAML.")
@click.argument("stack_name", type=str, required=True)
@click.option("--filename", "-f", type=str, required=False)
@click.option(
    "--ignore-version-mismatch",
    is_flag=True,
    help="Import stack components even if the installed version of ZenML "
    "is different from the one specified in the stack YAML file",
)
@click.pass_context
def import_stack(
    ctx: click.Context,
    stack_name: str,
    filename: Optional[str],
    ignore_version_mismatch: bool = False,
) -> None:
    """Import a stack from YAML.

    Args:
        ctx: The click context.
        stack_name: The name of the stack to import.
        filename: The filename to import the stack from.
        ignore_version_mismatch: Import stack components even if
            the installed version of ZenML is different from the
            one specified in the stack YAML file.
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

    # ask user for a new stack_name if current one already exists
    client = Client()
    if stack_name in [s.name for s in client.stacks]:
        stack_name = click.prompt(
            f"Stack `{stack_name}` already exists. "
            f"Please choose a different name.",
            type=str,
        )

    # import stack components
    component_ids = {}
    for component_type, component_config in data["components"].items():
        component_id = _import_stack_component(
            component_type=component_type,
            component_config=component_config,
        )
        component_ids[component_type + "_name"] = str(component_id)

    # register new stack
    ctx.invoke(
        register_stack,
        stack_name=stack_name,
        **component_ids,
    )


@stack.command("copy", help="Copy a stack to a new stack name.")
@click.argument("source_stack_name_or_id", type=str, required=True)
@click.argument("target_stack", type=str, required=True)
def copy_stack(
    source_stack_name_or_id: str,
    target_stack: str,
) -> None:
    """Copy a stack.

    Args:
        source_stack_name_or_id: The name or id of the stack to copy.
        target_stack: Name of the copied stack.
    """
    track_event(AnalyticsEvent.COPIED_STACK)

    client = Client()

    with console.status(f"Copying stack `{source_stack_name_or_id}`...\n"):
        try:
            stack_to_copy = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=source_stack_name_or_id
            )
        except KeyError:
            cli_utils.error(
                f"Stack `{source_stack_name_or_id}` cannot be copied as it "
                f"does not exist."
            )

        try:
            cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=target_stack
            )
            cli_utils.error(
                f"Can't copy stack because a stack with the name "
                f"'{target_stack}' already exists."
            )
        except KeyError:
            pass

        stack_to_copy.name = target_stack
        stack_to_copy.user = client.active_user.id
        stack_to_copy.project = client.active_project.id

        from zenml.models import StackModel

        copied_stack = StackModel.parse_obj(
            stack_to_copy.dict(exclude={"id", "created", "updated"})
        )
        client.register_stack(copied_stack)


@stack.command(
    "register-secrets",
    help="Interactively register all required secrets for a stack.",
)
@click.argument("stack_name_or_id", type=str, required=False)
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
    stack_name_or_id: Optional[str] = None,
) -> None:
    """Interactively registers all required secrets for a stack.

    Args:
        skip_existing: If `True`, skip asking for secret values that already
            exist.
        stack_name_or_id: Name of the stack for which to register secrets.
                          If empty, the active stack will be used.
    """
    cli_utils.print_active_config()

    from zenml.stack.stack import Stack

    client = Client()

    if stack_name_or_id:
        try:
            stack_model = cli_utils.get_stack_by_id_or_name_or_prefix(
                client=client, id_or_name_or_prefix=stack_name_or_id
            )
            stack_ = Stack.from_model(stack_model.to_hydrated_model())
        except KeyError:
            cli_utils.error(f"No stack found for name `{stack_name_or_id}`.")
    else:
        stack_ = Client().active_stack
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

        from zenml.secret import ArbitrarySecretSchema

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
