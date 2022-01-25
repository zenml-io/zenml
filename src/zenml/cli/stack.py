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
from zenml.enums import StackComponentType
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
@cli_utils.activate_integrations
def register_stack(
    stack_name: str,
    metadata_store_name: str,
    artifact_store_name: str,
    orchestrator_name: str,
    container_registry_name: Optional[str] = None,
) -> None:
    """Register a stack."""

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
            StackComponentType.CONTAINER_REGISTRY, name=container_registry_name
        )

    stack_ = Stack.from_components(name=stack_name, components=stack_components)
    repo.register_stack(stack_)
    cli_utils.declare(f"Stack `{stack_name}` successfully registered!")


@stack.command("list")
def list_stacks() -> None:
    """List all available stacks from service."""
    repo = Repository()

    if len(repo.stack_configurations) == 0:
        cli_utils.warning("No stacks registered!")
        return

    cli_utils.title("Stacks:")
    active_stack_name = repo.active_stack_name

    stack_dicts = []
    for stack_name, stack_configuration in repo.stack_configurations.items():
        is_active = stack_name == active_stack_name
        stack_config = {
            "ACTIVE": "*" if is_active else "",
            "NAME": stack_name,
            **{
                key.upper(): value
                for key, value in stack_configuration.dict().items()
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
    """Show details about the current active stack."""
    repo = Repository()
    active_stack_name = repo.active_stack_name
    stack_name = stack_name or active_stack_name

    stack_configurations = repo.stack_configurations
    if len(stack_configurations) == 0:
        cli_utils.warning("No stacks registered!")
        return

    try:
        stack_configuration = stack_configurations[stack_name]
    except KeyError:
        cli_utils.error(f"Stack `{stack_name}` does not exist.")
        return
    cli_utils.title("Stack:")

    if stack_name == active_stack_name:
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")

    cli_utils.declare(f"NAME: {stack_name}")
    for key, value in stack_configuration.dict().items():
        cli_utils.declare(f"{key.upper()}: {value}")


@stack.command("delete")
@click.argument("stack_name", type=str)
def delete_stack(stack_name: str) -> None:
    """Delete a stack."""
    Repository().deregister_stack(stack_name)
    cli_utils.declare(f"Deleted stack {stack_name}.")


@stack.command("set")
@click.argument("stack_name", type=str)
def set_active_stack(stack_name: str) -> None:
    """Sets a stack active."""
    Repository().activate_stack(stack_name)
    cli_utils.declare(f"Active stack: {stack_name}")


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    cli_utils.declare(f"Active stack: {Repository().active_stack_name}")


@stack.command("up")
@cli_utils.activate_integrations
def up_stack() -> None:
    """Provisions resources for the stack."""
    stack_ = Repository().active_stack
    cli_utils.declare(f"Provisioning resources for stack '{stack_.name}'.")
    stack_.provision()
    stack_.resume()


@stack.command("down")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
@cli_utils.activate_integrations
def down_stack(force: bool = False) -> None:
    """Suspends resources of the local stack deployment."""
    stack_ = Repository().active_stack

    if force:
        cli_utils.declare(
            f"Deprovisioning resources for stack '{stack_.name}'."
        )
        stack_.deprovision()
    else:
        cli_utils.declare(f"Suspending resources for stack '{stack_.name}'.")
        stack_.suspend()
