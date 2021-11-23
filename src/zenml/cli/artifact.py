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

from typing import List

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository


@cli.group()
def artifact() -> None:
    """Utilities for artifact store"""


@artifact.command("get")
def get_active_artifact_store() -> None:
    """Gets the artifact store of the active stack."""
    artifact_store_name = Repository().get_active_stack().artifact_store_name
    cli_utils.declare(f"Active artifact store: {artifact_store_name}")


@artifact.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("artifact_store_name", type=str)
@click.argument("artifact_store_type", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@cli_utils.activate_integrations
def register_artifact_store(
    artifact_store_name: str, artifact_store_type: str, args: List[str]
) -> None:
    """Register an artifact store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    # TODO [ENG-188]: Remove when we rework the registry logic
    from zenml.core.component_factory import artifact_store_factory

    comp = artifact_store_factory.get_single_component(artifact_store_type)
    artifact_store = comp(**parsed_args)
    service = repo.get_service()
    service.register_artifact_store(artifact_store_name, artifact_store)
    cli_utils.declare(
        f"Artifact Store `{artifact_store_name}` successfully registered!"
    )


@artifact.command("list")
def list_artifact_stores() -> None:
    """List all available artifact stores from service."""
    service = Repository().get_service()
    cli_utils.title("Artifact Stores:")
    cli_utils.echo_component_list(service.artifact_stores)


@artifact.command("delete")
@click.argument("artifact_store_name", type=str)
def delete_artifact_store(artifact_store_name: str) -> None:
    """Delete a artifact store."""
    service = Repository().get_service()
    service.delete_artifact_store(artifact_store_name)
    cli_utils.declare(f"Deleted artifact store: {artifact_store_name}")
