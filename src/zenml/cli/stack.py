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
from zenml.config.global_config import GlobalConfig
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
    "-s",
    "--step_operator",
    "step_operator_name",
    help="Name of the step operator for this stack.",
    type=str,
    required=False,
)
def register_stack(
    stack_name: str,
    metadata_store_name: str,
    artifact_store_name: str,
    orchestrator_name: str,
    container_registry_name: Optional[str] = None,
    step_operator_name: Optional[str] = None,
) -> None:
    """Register a stack."""
    cli_utils.print_active_profile()

    with console.status(f"Registering stack `{stack_name}`..."):
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

        if step_operator_name:
            stack_components[
                StackComponentType.STEP_OPERATOR
            ] = repo.get_stack_component(
                StackComponentType.STEP_OPERATOR,
                name=step_operator_name,
            )

        stack_ = Stack.from_components(
            name=stack_name, components=stack_components
        )
        repo.register_stack(stack_)
        cli_utils.declare(f"Stack `{stack_name}` successfully registered!")


@stack.command("list")
def list_stacks() -> None:
    """List all available stacks in the repository."""
    cli_utils.print_active_profile()

    repo = Repository()

    if len(repo.stack_configurations) == 0:
        cli_utils.warning("No stacks registered!")
        return

    global_stack = repo.active_profile.active_stack or ""

    stack_dicts = []
    for stack_name, stack_configuration in repo.stack_configurations.items():
        active_str = ""
        if stack_name == global_stack:
            active_str += ":crown:"
        if stack_name == repo.active_stack_name:
            active_str += ":point_right:"
        stack_config = {
            "ACTIVE": active_str,
            "STACK NAME": stack_name,
            **{
                component_type.value.upper(): value
                for component_type, value in stack_configuration.items()
            },
        }
        stack_dicts.append(stack_config)

    cli_utils.print_table(
        stack_dicts,
        caption=":crown: = globally active, :point_right: = locally active",
    )


@stack.command(
    "describe",
    help="Show details about the current active stack.",
)
@click.argument(
    "stack_name",
    type=click.STRING,
    required=False,
)
@click.option(
    "--global",
    "-g",
    "global_profile",
    is_flag=True,
    help="Describe the global active stack.",
)
def describe_stack(
    stack_name: Optional[str], global_profile: bool = False
) -> None:
    """Show details about a named stack or the active stack.

    If the `--global` flag is set, the global active stack will be shown,
    otherwise the repository local active stack is shown.
    """
    cli_utils.print_active_profile()

    repo = Repository()

    global_stack = repo.active_profile.active_stack or ""
    if global_profile:
        stack_name = stack_name or global_stack
    else:
        stack_name = stack_name or repo.active_stack_name

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
        cli_utils.error(f"Stack `{stack_name}` does not exist.")
        return

    cli_utils.print_stack_configuration(
        stack_configuration,
        locally_active=stack_name == repo.active_stack_name,
        globally_active=stack_name == global_stack,
        stack_name=stack_name,
    )


@stack.command("delete")
@click.argument("stack_name", type=str)
def delete_stack(stack_name: str) -> None:
    """Delete a stack."""
    cli_utils.print_active_profile()

    with console.status(f"Deleting stack `{stack_name}`...\n"):

        cfg = GlobalConfig()
        repo = Repository()

        if cfg.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted because it's globally "
                f"active. Please choose a different active global stack first "
                f"by running `zenml stack set --global STACK`."
            )
            return

        if repo.active_stack_name == stack_name:
            cli_utils.error(
                f"Stack {stack_name} cannot be deleted because it's locally "
                f"active. Please choose a different active stack first by "
                f"running `zenml stack set STACK`."
            )
            return

        Repository().deregister_stack(stack_name)
        cli_utils.declare(f"Deleted stack {stack_name}.")


@stack.command("set")
@click.argument("stack_name", type=str)
@click.option(
    "--global",
    "-g",
    "global_profile",
    is_flag=True,
    help="Set the global active stack",
)
def set_active_stack(stack_name: str, global_profile: bool = False) -> None:
    """Sets a stack as active.

    If the `--global` flag is set, the global active stack will be set,
    otherwise the repository active stack takes precedence.
    """
    cli_utils.print_active_profile()

    scope = "local"
    if global_profile:
        scope = "global"

    repo = Repository()

    with console.status(
        f"Setting the {scope} active stack for active profile "
        f"{repo.active_profile_name} to `{stack_name}`..."
    ):

        if global_profile:
            repo.active_profile.activate_stack(stack_name)
        else:
            repo.activate_stack(stack_name)

        cli_utils.declare(
            f"Active {scope} stack for active profile "
            f"`{repo.active_profile_name}`: `{stack_name}`"
        )


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    cli_utils.print_active_profile()

    with console.status("Getting the active stack..."):

        repo = Repository()
        cli_utils.declare(
            f"Globally active stack for active profile "
            f"`{repo.active_profile_name}` is: "
            f"`{repo.active_profile.active_stack}`"
        )
        cli_utils.declare(
            f"Locally active stack for active profile "
            f"`{repo.active_profile_name}` is: `{repo.active_stack_name}`"
        )


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the active stack."""
    cli_utils.print_active_profile()

    stack_ = Repository().active_stack
    cli_utils.declare(f"Provisioning resources for stack '{stack_.name}'.")
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
