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

from typing import Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository


@cli.group("container-registry")
def container_registry() -> None:
    """Utilities for container registries."""


@container_registry.command("get")
def get_active_container_registry() -> None:
    """Gets the container registry of the active stack."""
    name = Repository().get_active_stack().container_registry_name
    if name:
        cli_utils.declare(f"Active container registry: {name}")
    else:
        cli_utils.declare(
            f"No container registry set for current active stack: {Repository().get_active_stack_key()}"
        )


@container_registry.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument(
    "name",
    required=True,
    type=click.STRING,
)
@click.option(
    "--uri",
    "-u",
    help="The URI for the container registry to register.",
    required=True,
    type=click.STRING,
)
def register_container_registry(name: str, uri: str) -> None:
    """Register a container registry."""

    from zenml.container_registries import BaseContainerRegistry

    repo = Repository()
    registry = BaseContainerRegistry(uri=uri, repo_path=repo.path)
    repo.get_service().register_container_registry(name, registry)
    cli_utils.declare(f"Container registry `{name}` successfully registered!")


@container_registry.command("list")
def list_container_registries() -> None:
    """List all available container registries from service."""
    repo = Repository()
    service = repo.get_service()
    if len(service.container_registries) == 0:
        cli_utils.warning("No container registries registered!")
        return

    active_container_registry = str(
        repo.get_active_stack().container_registry_name
    )
    service = repo.get_service()
    cli_utils.title("Container registries:")
    cli_utils.print_table(
        cli_utils.format_component_list(
            service.container_registries, active_container_registry
        )
    )


@container_registry.command(
    "describe",
    help="Show details about the current active container registry.",
)
@click.argument(
    "container_registry_name",
    type=click.STRING,
    required=False,
)
def describe_container_registry(
    container_registry_name: Optional[str],
) -> None:
    """Show details about the current active container registry."""
    repo = Repository()
    container_registry_name = container_registry_name or str(
        repo.get_active_stack().container_registry_name
    )

    container_registries = repo.get_service().container_registries
    if len(container_registries) == 0:
        cli_utils.warning("No container registries registered!")
        return

    try:
        container_registry_details = container_registries[
            container_registry_name
        ]
    except KeyError:
        cli_utils.error(
            f"Container registry `{container_registry_name}` does not exist."
        )
        return
    cli_utils.title("Container Registry:")
    if (
        repo.get_active_stack().container_registry_name
        == container_registry_name
    ):
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")
    cli_utils.declare(f"NAME: {container_registry_name}")
    cli_utils.print_component_properties(container_registry_details.dict())


@container_registry.command("delete")
@click.argument("container_registry_name", type=str)
def delete_container_registry(container_registry_name: str) -> None:
    """Delete a container registry."""
    service = Repository().get_service()
    service.delete_container_registry(container_registry_name)
    cli_utils.declare(f"Deleted container registry: {container_registry_name}")
