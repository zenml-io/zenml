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
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import click

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import _component_display_name, print_stacks_table
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import (
    IllegalOperationError,
    ProvisioningError,
    StackExistsError,
)
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.utils.yaml_utils import read_yaml, write_yaml


# Stacks
@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
)
def stack() -> None:
    """Stacks to define various environments."""
    cli_utils.print_active_config()


@stack.command(
    "register",
    context_settings=dict(ignore_unknown_options=True),
    help="Register a stack with components.",
)
@click.argument("stack_name", type=str, required=True)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store",
    help="Name of the artifact store for this stack.",
    type=str,
    required=True,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator",
    help="Name of the orchestrator for this stack.",
    type=str,
    required=True,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry",
    help="Name of the container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-x",
    "--secrets_manager",
    "secrets_manager",
    help="Name of the secrets manager for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator",
    help="Name of the step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store",
    help="Name of the feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer",
    help="Name of the model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker",
    help="Name of the experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter",
    help="Name of the alerter for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator",
    help="Name of the annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator",
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
    artifact_store: str,
    orchestrator: str,
    container_registry: Optional[str] = None,
    secrets_manager: Optional[str] = None,
    step_operator: Optional[str] = None,
    feature_store: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    alerter: Optional[str] = None,
    annotator: Optional[str] = None,
    data_validator: Optional[str] = None,
    set_stack: bool = False,
    share: bool = False,
) -> None:
    """Register a stack.

    Args:
        stack_name: Unique name of the stack
        artifact_store: Name of the artifact store for this stack.
        orchestrator: Name of the orchestrator for this stack.
        container_registry: Name of the container registry for this stack.
        secrets_manager: Name of the secrets manager for this stack.
        step_operator: Name of the step operator for this stack.
        feature_store: Name of the feature store for this stack.
        model_deployer: Name of the model deployer for this stack.
        experiment_tracker: Name of the experiment tracker for this stack.
        alerter: Name of the alerter for this stack.
        annotator: Name of the annotator for this stack.
        data_validator: Name of the data validator for this stack.
        set_stack: Immediately set this stack as active.
        share: Share the stack with other users.
    """
    with console.status(f"Registering stack '{stack_name}'...\n"):
        client = Client()

        components: Dict[StackComponentType, Union[str, UUID]] = dict()

        components[StackComponentType.ARTIFACT_STORE] = artifact_store
        components[StackComponentType.ORCHESTRATOR] = orchestrator

        if alerter:
            components[StackComponentType.ALERTER] = alerter
        if annotator:
            components[StackComponentType.ANNOTATOR] = annotator
        if data_validator:
            components[StackComponentType.DATA_VALIDATOR] = data_validator
        if feature_store:
            components[StackComponentType.FEATURE_STORE] = feature_store
        if model_deployer:
            components[StackComponentType.MODEL_DEPLOYER] = model_deployer
        if secrets_manager:
            components[StackComponentType.SECRETS_MANAGER] = secrets_manager
        if step_operator:
            components[StackComponentType.STEP_OPERATOR] = step_operator
        if experiment_tracker:
            components[
                StackComponentType.EXPERIMENT_TRACKER
            ] = experiment_tracker
        if container_registry:
            components[
                StackComponentType.CONTAINER_REGISTRY
            ] = container_registry

        # click<8.0.0 gives flags a default of None
        if share is None:
            share = False

        try:
            created_stack = client.create_stack(
                name=stack_name,
                components=components,
                is_shared=share,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            f"Stack '{created_stack.name}' successfully registered!"
        )

    if set_stack:
        client.activate_stack(created_stack.id)

        scope = "repository" if client.uses_local_configuration else "global"
        cli_utils.declare(f"Active {scope} stack set to:'{created_stack.name}'")


@stack.command(
    "update",
    context_settings=dict(ignore_unknown_options=True),
    help="Update a stack with new components.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store",
    help="Name of the new artifact store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator",
    help="Name of the new orchestrator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry",
    help="Name of the new container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator",
    help="Name of the new step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-x",
    "--secrets_manager",
    "secrets_manager",
    help="Name of the new secrets manager for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store",
    help="Name of the new feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer",
    help="Name of the new model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker",
    help="Name of the new experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter",
    help="Name of the new alerter for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator",
    help="Name of the new annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator",
    help="Name of the data validator for this stack.",
    type=str,
    required=False,
)
def update_stack(
    stack_name_or_id: Optional[str] = None,
    artifact_store: Optional[str] = None,
    orchestrator: Optional[str] = None,
    container_registry: Optional[str] = None,
    step_operator: Optional[str] = None,
    secrets_manager: Optional[str] = None,
    feature_store: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    alerter: Optional[str] = None,
    annotator: Optional[str] = None,
    data_validator: Optional[str] = None,
) -> None:
    """Update a stack.

    Args:
        stack_name_or_id: Name or id of the stack to update.
        artifact_store: Name of the new artifact store for this stack.
        orchestrator: Name of the new orchestrator for this stack.
        container_registry: Name of the new container registry for this stack.
        step_operator: Name of the new step operator for this stack.
        secrets_manager: Name of the new secrets manager for this stack.
        feature_store: Name of the new feature store for this stack.
        model_deployer: Name of the new model deployer for this stack.
        experiment_tracker: Name of the new experiment tracker for this
            stack.
        alerter: Name of the new alerter for this stack.
        annotator: Name of the new annotator for this stack.
        data_validator: Name of the new data validator for this stack.
    """
    client = Client()

    with console.status("Updating stack...\n"):

        updates: Dict[StackComponentType, List[Union[str, UUID]]] = dict()
        if artifact_store:
            updates[StackComponentType.ARTIFACT_STORE] = [artifact_store]
        if alerter:
            updates[StackComponentType.ALERTER] = [alerter]
        if annotator:
            updates[StackComponentType.ANNOTATOR] = [annotator]
        if container_registry:
            updates[StackComponentType.CONTAINER_REGISTRY] = [
                container_registry
            ]
        if data_validator:
            updates[StackComponentType.DATA_VALIDATOR] = [data_validator]
        if experiment_tracker:
            updates[StackComponentType.EXPERIMENT_TRACKER] = [
                experiment_tracker
            ]
        if feature_store:
            updates[StackComponentType.FEATURE_STORE] = [feature_store]
        if model_deployer:
            updates[StackComponentType.MODEL_DEPLOYER] = [model_deployer]
        if orchestrator:
            updates[StackComponentType.ORCHESTRATOR] = [orchestrator]
        if secrets_manager:
            updates[StackComponentType.SECRETS_MANAGER] = [secrets_manager]
        if step_operator:
            updates[StackComponentType.STEP_OPERATOR] = [step_operator]

        try:
            updated_stack = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                component_updates=updates,
            )

        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

        cli_utils.declare(f"Stack `{updated_stack.name}` successfully updated!")


@stack.command(
    "share",
    context_settings=dict(ignore_unknown_options=True),
    help="Share a stack and all its components.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "--recursive",
    "-r",
    "recursive",
    is_flag=True,
    help="Recursively also share all stack components if they are private.",
)
def share_stack(
    stack_name_or_id: Optional[str], recursive: bool = False
) -> None:
    """Share a stack with your team.

    Args:
        stack_name_or_id: Name or id of the stack to share.
        recursive: Recursively also share all components
    """
    client = Client()

    with console.status("Sharing the stack...\n"):
        try:
            if recursive:
                stack_to_update = client.get_stack(
                    name_id_or_prefix=stack_name_or_id
                )
                for c_type, components in stack_to_update.components.items():
                    for component in components:
                        client.update_stack_component(
                            name_id_or_prefix=component.id,
                            component_type=c_type,
                            is_shared=True,
                        )
            updated_stack = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                is_shared=True,
            )
        except (KeyError, IllegalOperationError, StackExistsError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(f"Stack `{updated_stack.name}` successfully shared!")


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
    stack_name_or_id: Optional[str] = None,
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
    client = Client()

    with console.status("Updating the stack...\n"):
        stack_component_update: Dict[StackComponentType, List[Any]] = dict()

        if container_registry_flag:
            stack_component_update[StackComponentType.CONTAINER_REGISTRY] = []

        if step_operator_flag:
            stack_component_update[StackComponentType.STEP_OPERATOR] = []

        if secrets_manager_flag:
            stack_component_update[StackComponentType.SECRETS_MANAGER] = []

        if feature_store_flag:
            stack_component_update[StackComponentType.FEATURE_STORE] = []

        if model_deployer_flag:
            stack_component_update[StackComponentType.MODEL_DEPLOYER] = []

        if experiment_tracker_flag:
            stack_component_update[StackComponentType.EXPERIMENT_TRACKER] = []

        if alerter_flag:
            stack_component_update[StackComponentType.ALERTER] = []

        if annotator_flag:
            stack_component_update[StackComponentType.ANNOTATOR] = []

        if data_validator_flag:
            stack_component_update[StackComponentType.DATA_VALIDATOR] = []

        try:
            updated_stack = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                component_updates=stack_component_update,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(f"Stack `{updated_stack.name}` successfully updated!")


@stack.command("rename", help="Rename a stack.")
@click.argument("stack_name_or_id", type=str, required=True)
@click.argument("new_stack_name", type=str, required=True)
def rename_stack(
    stack_name_or_id: str,
    new_stack_name: str,
) -> None:
    """Rename a stack.

    Args:
        stack_name_or_id: Name of the stack to rename.
        new_stack_name: New name of the stack.
    """
    client = Client()

    with console.status("Renaming stack...\n"):
        try:
            client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                name=new_stack_name,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(
            f"Stack `{stack_name_or_id}` successfully renamed to `"
            f"{new_stack_name}`!"
        )


@stack.command("list")
@click.option("--just-mine", "-m", is_flag=True, required=False)
def list_stacks(just_mine: bool = False) -> None:
    """List all available stacks.

    Args:
        just_mine: To list only the stacks that the current user has created.
    """
    client = Client()
    with console.status("Listing stacks...\n"):
        if just_mine:
            stacks = client.list_stacks(user_name_or_id=client.active_user.id)
        else:
            stacks = client.list_stacks()

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
def describe_stack(stack_name_or_id: Optional[str] = None) -> None:
    """Show details about a named stack or the active stack.

    Args:
        stack_name_or_id: Name of the stack to describe.
    """
    client = Client()

    with console.status("Describing stack...\n"):
        try:
            stack_ = client.get_stack(name_id_or_prefix=stack_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))

        cli_utils.print_stack_configuration(
            stack=stack_,
            active=stack_.id == client.active_stack_model.id,
        )


@stack.command("delete", help="Delete a stack given its name.")
@click.argument("stack_name_or_id", type=str)
@click.option("--yes", "-y", is_flag=True, required=False)
def delete_stack(stack_name_or_id: str, yes: bool = False) -> None:
    """Delete a stack.

    Args:
        stack_name_or_id: Name or id of the stack to delete.
        yes: Stack will be deleted without prompting for
            confirmation.
    """
    confirmation = yes or cli_utils.confirmation(
        f"This will delete stack '{stack_name_or_id}'. \n"
        "Are you sure you want to proceed?"
    )

    if not confirmation:
        cli_utils.declare("Stack deletion canceled.")
        return

    with console.status(f"Deleting stack '{stack_name_or_id}'...\n"):
        client = Client()
        try:
            client.delete_stack(stack_name_or_id)
        except (KeyError, ValueError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(f"Deleted stack '{stack_name_or_id}'.")


@stack.command("set", help="Sets a stack as active.")
@click.argument("stack_name_or_id", type=str)
def set_active_stack_command(stack_name_or_id: str) -> None:
    """Sets a stack as active.

    Args:
        stack_name_or_id: Name of the stack to set as active.
    """
    client = Client()
    scope = "repository" if client.uses_local_configuration else "global"

    with console.status(
        f"Setting the {scope} active stack to '{stack_name_or_id}'..."
    ):
        try:
            client.activate_stack(stack_name_id_or_prefix=stack_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            f"Active {scope} stack set to: "
            f"'{client.active_stack_model.name}'"
        )


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    scope = "repository" if Client().uses_local_configuration else "global"

    with console.status("Getting the active stack..."):
        client = Client()
        try:
            cli_utils.declare(
                f"The {scope} active stack is: '{client.active_stack_model.name}'"
            )
        except KeyError as err:
            cli_utils.error(str(err))


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the active stack."""
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
    "--force",
    "-f",
    "force",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_stack(force: bool = False) -> None:
    """Suspends resources of the active stack deployment.

    Args:
        force: Deprovisions local resources instead of suspending them.
    """
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


@stack.command("export", help="Exports a stack to a YAML file.")
@click.argument("stack_name_or_id", type=str, required=False)
@click.argument("filename", type=str, required=False)
@track(AnalyticsEvent.EXPORT_STACK)
def export_stack(
    stack_name_or_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """Export a stack to YAML.

    Args:
        stack_name_or_id: The name of the stack to export.
        filename: The filename to export the stack to.
    """
    # Get configuration of given stack
    client = Client()
    try:
        stack_to_export = client.get_stack(name_id_or_prefix=stack_name_or_id)
    except KeyError as err:
        cli_utils.error(str(err))

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
    component_type: StackComponentType, component_dict: Dict[str, Any]
) -> UUID:
    """Import a single stack component with given type/config.

    Args:
        component_type: The type of component to import.
        component_dict: Dict representation of the component to import.

    Returns:
        The ID of the imported component.
    """
    name = component_dict["name"]
    flavor = component_dict["flavor"]
    config = component_dict["configuration"]

    # make sure component can be registered, otherwise ask for new name
    client = Client()

    try:
        component = client.get_stack_component(
            name_id_or_prefix=name,
            component_type=component_type,
        )
        if component.configuration == config:
            return component.id
        else:
            display_name = _component_display_name(component_type)
            name = click.prompt(
                f"A component of type '{display_name}' with the name "
                f"'{name}' already exists, "
                f"but is configured differently. "
                f"Please choose a different name.",
                type=str,
            )
    except KeyError:
        pass

    component = client.create_stack_component(
        name=name,
        component_type=component_type,
        flavor=flavor,
        configuration=config,
    )
    return component.id


@stack.command("import", help="Import a stack from YAML.")
@click.argument("stack_name", type=str, required=True)
@click.option("--filename", "-f", type=str, required=False)
@click.option(
    "--ignore-version-mismatch",
    is_flag=True,
    help="Import stack components even if the installed version of ZenML "
    "is different from the one specified in the stack YAML file",
)
@track(AnalyticsEvent.IMPORT_STACK)
def import_stack(
    stack_name: str,
    filename: Optional[str],
    ignore_version_mismatch: bool = False,
) -> None:
    """Import a stack from YAML.

    Args:
        stack_name: The name of the stack to import.
        filename: The filename to import the stack from.
        ignore_version_mismatch: Import stack components even if
            the installed version of ZenML is different from the
            one specified in the stack YAML file.
    """
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
    if client.list_stacks(name=stack_name):
        stack_name = click.prompt(
            f"Stack `{stack_name}` already exists. Please choose a different "
            f"name",
            type=str,
        )

    # import stack components
    component_ids = {}
    for component_type_str, component_config in data["components"].items():
        component_type = StackComponentType(component_type_str)

        component_id = _import_stack_component(
            component_type=component_type,
            component_dict=component_config,
        )
        component_ids[component_type] = component_id

    Client().create_stack(
        name=stack_name, components=component_ids, is_shared=False
    )


@stack.command("copy", help="Copy a stack to a new stack name.")
@click.argument("source_stack_name_or_id", type=str, required=True)
@click.argument("target_stack", type=str, required=True)
@click.option(
    "--share",
    "share",
    is_flag=True,
    help="Use this flag to share this stack with other users.",
    type=click.BOOL,
)
@track(AnalyticsEvent.COPIED_STACK)
def copy_stack(
    source_stack_name_or_id: str, target_stack: str, share: bool = False
) -> None:
    """Copy a stack.

    Args:
        source_stack_name_or_id: The name or id of the stack to copy.
        target_stack: Name of the copied stack.
        share: Share the stack with other users.
    """
    client = Client()

    with console.status(f"Copying stack `{source_stack_name_or_id}`...\n"):
        try:
            stack_to_copy = client.get_stack(
                name_id_or_prefix=source_stack_name_or_id
            )
        except KeyError as err:
            cli_utils.error(str(err))

        component_mapping: Dict[StackComponentType, Union[str, UUID]] = {}

        for c_type, c_list in stack_to_copy.components.items():
            if c_list:
                component_mapping[c_type] = c_list[0].id

        client.create_stack(
            name=target_stack,
            components=component_mapping,
            is_shared=share,
        )


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

    stack_model = client.get_stack(name_id_or_prefix=stack_name_or_id)

    stack_ = Stack.from_model(stack_model)
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
