#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""CLI functionality to interact with artifacts."""


from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories
from zenml.logger import get_logger

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def artifact() -> None:
    """List or delete artifacts."""


@artifact.command("list", help="List all artifacts.")
def list_artifacts() -> None:
    """List all artifacts."""
    cli_utils.print_active_config()
    artifacts = Client().list_artifacts()

    if not artifacts:
        logger.info("No artifacts found.")
        return

    cli_utils.print_pydantic_models(
        artifacts,
        exclude_columns=[
            "created",
            "updated",
            "user",
            "project",
            "producer_step_run_id",
        ],
    )


@artifact.command("delete", help="Delete an artifact.")
@click.argument("artifact_id")
@click.option(
    "--only-metadata",
    "-m",
    is_flag=True,
    help="Only delete metadata and not the actual artifact.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_artifact(
    artifact_id: str, only_metadata: bool = False, yes: bool = False
) -> None:
    """Delete an artifact.

    Args:
        artifact_id: ID of the artifact to delete.
        only_metadata: If set, only delete metadata and not the actual artifact.
        yes: If set, don't ask for confirmation.
    """
    cli_utils.print_active_config()

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete artifact '{artifact_id}'?"
        )
        if not confirmation:
            cli_utils.declare("Artifact deletion canceled.")
            return

    try:
        Client().delete_artifact(
            artifact_id=UUID(artifact_id),
            only_metadata=only_metadata,
        )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Artifact '{artifact_id}' deleted.")
