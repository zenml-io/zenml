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
from zenml.core.repo import Repository
from zenml.stacks import BaseStack


# Stacks
@cli.group()
def stack() -> None:
    """Stacks to define various environments."""


@stack.command("register", context_settings=dict(ignore_unknown_options=True))
@click.argument("stack_name", type=click.STRING, required=True)
@click.option(
    "-m",
    "--metadata-store",
    help="The name of the metadata store that you would like to register as part of the new stack.",
    type=click.STRING,
    required=True,
)
@click.option(
    "-a",
    "--artifact-store",
    help="The name of the artifact store that you would like to register as part of the new stack.",
    type=click.STRING,
    required=True,
)
@click.option(
    "-o",
    "--orchestrator",
    help="The name of the orchestrator that you would like to register as part of the new stack.",
    type=click.STRING,
    required=True,
)
@click.option(
    "-c",
    "--container_registry",
    help="The name of the container_registry that you would like to register as part of the new stack.",
    type=click.STRING,
    required=False,
)
def register_stack(
    stack_name: str,
    metadata_store: str,
    artifact_store: str,
    orchestrator: str,
    container_registry: Optional[str] = None,
) -> None:
    """Register a stack."""

    service = Repository().get_service()
    stack = BaseStack(
        artifact_store_name=artifact_store,
        orchestrator_name=orchestrator,
        metadata_store_name=metadata_store,
        container_registry_name=container_registry,
    )
    service.register_stack(stack_name, stack)
    cli_utils.declare(f"Stack `{stack_name}` successfully registered!")


@stack.command("list")
def list_stacks() -> None:
    """List all available stacks from service."""
    repo = Repository()
    service = repo.get_service()
    if len(service.stacks) == 0:
        cli_utils.warning("No stacks registered!")
        return

    cli_utils.title("Stacks:")
    # TODO [ENG-144]: once there is a common superclass for Stack/ArtifactStore etc.,
    #  remove the mypy ignore
    active_stack = repo.get_active_stack_key()
    cli_utils.print_table(
        cli_utils.format_component_list(service.stacks, active_stack)  # type: ignore[arg-type]
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
def describe_stack(stack_name: Optional[str]) -> None:
    """Show details about the current active stack."""
    repo = Repository()
    stack_name = stack_name or repo.get_active_stack_key()

    stacks = repo.get_service().stacks
    if len(stacks) == 0:
        cli_utils.warning("No stacks registered!")
        return

    try:
        stack_details = stacks[stack_name]
    except KeyError:
        cli_utils.error(f"Stack `{stack_name}` does not exist.")
        return
    cli_utils.title("Stack:")
    if repo.get_active_stack_key() == stack_name:
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")
    cli_utils.declare(f"NAME: {stack_name}")
    cli_utils.print_component_properties(stack_details.dict())


@stack.command("delete")
@click.argument("stack_name", type=str)
def delete_stack(stack_name: str) -> None:
    """Delete a stack."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting stack: {stack_name}")
    service.delete_stack(stack_name)
    cli_utils.declare("Deleted!")


@stack.command("set")
@click.argument("stack_name", type=str)
def set_active_stack(stack_name: str) -> None:
    """Sets a stack active."""
    repo = Repository()
    repo.set_active_stack(stack_name)
    cli_utils.declare(f"Active stack: {stack_name}")


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    repo = Repository()
    key = repo.get_active_stack_key()
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
