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
from typing import TYPE_CHECKING, List, Optional, cast

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore


@cli.group("artifact-store")
def artifact_store() -> None:
    """Utilities for artifact store"""


@artifact_store.command("get")
def get_active_artifact_store() -> None:
    """Gets the artifact store of the active stack."""
    artifact_store_name = Repository().get_active_stack().artifact_store_name
    cli_utils.declare(f"Active artifact store: {artifact_store_name}")


@artifact_store.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument(
    "name",
    type=click.STRING,
    required=True,
)
@click.option(
    "--type",
    "-t",
    help="The type of the artifact store to register.",
    required=True,
    type=click.STRING,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@cli_utils.activate_integrations
def register_artifact_store(name: str, type: str, args: List[str]) -> None:
    """Register an artifact store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    # TODO [ENG-188]: Remove when we rework the registry logic
    from zenml.core.component_factory import artifact_store_factory

    comp = artifact_store_factory.get_single_component(type)
    artifact_store = comp(repo_path=repo.path, **parsed_args)
    service = repo.get_service()
    service.register_artifact_store(
        name, cast("BaseArtifactStore", artifact_store)
    )
    cli_utils.declare(f"Artifact Store `{name}` successfully registered!")


@artifact_store.command("list")
def list_artifact_stores() -> None:
    """List all available artifact stores from service."""
    repo = Repository()
    service = repo.get_service()
    if len(service.artifact_stores) == 0:
        cli_utils.warning("No artifact stores registered!")
        return

    active_artifact_store = repo.get_active_stack().artifact_store_name
    cli_utils.title("Artifact Stores:")
    cli_utils.print_table(
        cli_utils.format_component_list(
            service.artifact_stores, active_artifact_store
        )
    )


@artifact_store.command(
    "describe", help="Show details about the current active artifact store."
)
@click.argument(
    "artifact_store_name",
    type=click.STRING,
    required=False,
)
def describe_artifact_store(artifact_store_name: Optional[str]) -> None:
    """Show details about the current active artifact store."""
    repo = Repository()
    artifact_store_name = (
        artifact_store_name or repo.get_active_stack().artifact_store_name
    )

    artifact_stores = repo.get_service().artifact_stores
    if len(artifact_stores) == 0:
        cli_utils.warning("No artifact stores registered!")
        return

    try:
        artifact_store_details = artifact_stores[artifact_store_name]
    except KeyError:
        cli_utils.error(
            f"Artifact store `{artifact_store_name}` does not exist."
        )
        return
    cli_utils.title("Artifact Store:")
    if repo.get_active_stack().artifact_store_name == artifact_store_name:
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")
    cli_utils.declare(f"NAME: {artifact_store_name}")
    cli_utils.print_component_properties(artifact_store_details.dict())


@artifact_store.command("delete")
@click.argument("artifact_store_name", type=str)
def delete_artifact_store(artifact_store_name: str) -> None:
    """Delete a artifact store."""
    service = Repository().get_service()
    service.delete_artifact_store(artifact_store_name)
    cli_utils.declare(f"Deleted artifact store: {artifact_store_name}")
