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
@click.argument("container_registry_name", type=str)
@click.argument("container_registry_uri", type=str)
def register_container_registry(
    container_registry_name: str, container_registry_uri: str
) -> None:
    """Register a container registry."""

    from zenml.container_registry.base_container_registry import (
        BaseContainerRegistry,
    )

    registry = BaseContainerRegistry(uri=container_registry_uri)
    service = Repository().get_service()
    service.register_container_registry(container_registry_name, registry)
    cli_utils.declare(
        f"Container registry `{container_registry_name}` successfully registered!"
    )


@container_registry.command("list")
def list_container_registries() -> None:
    """List all available container registries from service."""
    service = Repository().get_service()
    cli_utils.title("Container registries:")
    cli_utils.echo_component_list(service.container_registries)


@container_registry.command("delete")
@click.argument("container_registry_name", type=str)
def delete_container_registry(container_registry_name: str) -> None:
    """Delete a container registry."""
    service = Repository().get_service()
    service.delete_container_registry(container_registry_name)
    cli_utils.declare(f"Deleted container registry: {container_registry_name}")
