#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
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
from zenml.new_core import Repository, Stack


# Stacks
@cli.group()
def stack() -> None:
    """Stacks to define various environments."""


@stack.command("register", context_settings=dict(ignore_unknown_options=True))
@click.argument("stack_name", type=str, required=True)
@click.option(
    "-m",
    "--metadata-store",
    help="The name of the metadata store that you would like to register as part of the new stack.",
    type=str,
    required=True,
)
@click.option(
    "-a",
    "--artifact-store",
    help="The name of the artifact store that you would like to register as part of the new stack.",
    type=str,
    required=True,
)
@click.option(
    "-o",
    "--orchestrator",
    help="The name of the orchestrator that you would like to register as part of the new stack.",
    type=str,
    required=True,
)
@click.option(
    "-c",
    "--container_registry",
    help="The name of the container_registry that you would like to register as part of the new stack.",
    type=str,
    required=False,
)
@cli_utils.activate_integrations
def register_stack(
    stack_name: str,
    metadata_store: str,
    artifact_store: str,
    orchestrator: str,
    container_registry: Optional[str] = None,
) -> None:
    """Register a stack."""

    repo = Repository()

    stack_components = {
        "metadata_store": repo.get_stack_component(
            StackComponentType.METADATA_STORE, name=metadata_store
        ),
        "artifact_store": repo.get_stack_component(
            StackComponentType.ARTIFACT_STORE, name=artifact_store
        ),
        "orchestrator": repo.get_stack_component(
            StackComponentType.ORCHESTRATOR, name=orchestrator
        ),
    }

    if container_registry:
        stack_components["container_registry"] = repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, name=container_registry
        )

    repo.register_stack(Stack(name=stack_name, **stack_components))
    cli_utils.declare(f"Stack `{stack_name}` successfully registered!")


@stack.command("list")
def list_stacks() -> None:
    """List all available stacks from service."""
    repo = Repository()

    if len(repo._config.stacks) == 0:
        cli_utils.warning("No stacks registered!")
        return

    cli_utils.title("Stacks:")
    active_stack_name = repo._config.active_stack_name

    stack_dicts = []
    for stack_name, stack_configuration in repo._config.stacks.items():
        is_active = stack_name == active_stack_name
        stack_config = {
            "ACTIVE": "*" if is_active else "",
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
    active_stack_name = repo._config.active_stack_name
    stack_name = stack_name or active_stack_name

    stacks = repo._config.stacks
    if len(stacks) == 0:
        cli_utils.warning("No stacks registered!")
        return

    try:
        stack_configuration = stacks[stack_name]
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
    key = Repository()._config.active_stack_name
    cli_utils.declare(f"Active stack: {key}")


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the stack."""
    active_stack = Repository().get_active_stack()
    orchestrator_name = active_stack.orchestrator_name

    cli_utils.declare(
        f"Bootstrapping resources for orchestrator: `{orchestrator_name}`. "
        f"This might take a few seconds..."
    )
    active_stack.orchestrator.up()


@stack.command("down")
def down_stack() -> None:
    """Tears down resources for the stack."""
    active_stack = Repository().get_active_stack()
    orchestrator_name = active_stack.orchestrator_name

    cli_utils.declare(
        f"Tearing down resources for orchestrator: `{orchestrator_name}`."
    )
    active_stack.orchestrator.down()
    cli_utils.declare(
        f"Orchestrator: `{orchestrator_name}` resources are now torn down."
    )
