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
from functools import partial
from typing import Any, List, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import ArtifactFilter
from zenml.utils.pagination_utils import depaginate
from zenml.utils.uuid_utils import is_valid_uuid

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def artifact() -> None:
    """List or delete artifacts."""


@cli_utils.list_options(ArtifactFilter)
@artifact.command("list", help="List all artifacts.")
def list_artifacts(**kwargs: Any) -> None:
    """List all artifacts.

    Args:
        **kwargs: Keyword arguments to filter artifacts.
    """
    artifacts = Client().list_artifacts(**kwargs)

    if not artifacts:
        cli_utils.declare("No artifacts found.")
        return

    cli_utils.print_pydantic_models(
        artifacts,
        exclude_columns=[
            "created",
            "updated",
            "user",
            "workspace",
            "producer_step_run_id",
            "run_metadata",
            "artifact_store_id",
        ],
    )


@artifact.command("delete", help="Delete an artifact.")
@click.argument("artifact_name_or_id")
@click.option(
    "--version",
    "-v",
    default=None,
    type=str,
    help="Version of the artifact to delete.",
)
@click.option(
    "--only-artifact",
    "-a",
    is_flag=True,
    help="Only delete the artifact itself but not its metadata.",
)
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
    artifact_name_or_id: str,
    version: Optional[str] = None,
    only_artifact: bool = False,
    only_metadata: bool = False,
    yes: bool = False,
) -> None:
    """Delete an artifact by ID or name.

    If an artifact name without a version is provided, all artifact versions
    with that name will be deleted.

    Args:
        artifact_name_or_id: Name or ID of the artifact to delete.
        version: Version of the artifact to delete.
        only_artifact: If set, only delete the artifact but not its metadata.
        only_metadata: If set, only delete metadata and not the actual artifact.
        yes: If set, don't ask for confirmation.
    """
    is_uuid = is_valid_uuid(artifact_name_or_id)

    if not yes:
        if is_uuid:
            confirmation = cli_utils.confirmation(
                f"Are you sure you want to delete artifact "
                f"'{artifact_name_or_id}'?"
            )
        elif version:
            confirmation = cli_utils.confirmation(
                f"Are you sure you want to delete version '{version}' of "
                f"artifact '{artifact_name_or_id}'?"
            )
        else:
            confirmation = cli_utils.confirmation(
                f"Are you sure you want to delete all versions of artifact "
                f"'{artifact_name_or_id}'?"
            )
        if not confirmation:
            cli_utils.declare("Artifact deletion canceled.")
            return

    try:
        versions: List[Optional[str]] = [version]
        if not is_uuid and not version:
            artifact_models = depaginate(
                partial(Client().list_artifacts, name=artifact_name_or_id)
            )
            versions = [
                str(artifact_model.version)
                for artifact_model in artifact_models
            ]
        for version_ in versions:
            Client().delete_artifact(
                name_id_or_prefix=artifact_name_or_id,
                version=version_,
                delete_metadata=not only_artifact,
                delete_from_artifact_store=not only_metadata,
            )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        if is_uuid:
            cli_utils.declare(f"Artifact '{artifact_name_or_id}' deleted.")
        elif version:
            cli_utils.declare(
                f"Version '{version}' of artifact '{artifact_name_or_id}' "
                f"deleted."
            )
        else:
            cli_utils.declare(
                f"All versions of artifact '{artifact_name_or_id}' deleted."
            )


@artifact.command("prune", help="Delete all unused artifacts.")
@click.option(
    "--only-artifact",
    "-a",
    is_flag=True,
    help="Only delete the artifact itself but not its metadata.",
)
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
def prune_artifacts(
    only_artifact: bool = False, only_metadata: bool = False, yes: bool = False
) -> None:
    """Delete all unused artifacts.

    Args:
        only_artifact: If set, only delete the artifact but not its metadata.
        only_metadata: If set, only delete metadata and not the actual artifact.
        yes: If set, don't ask for confirmation.
    """
    client = Client()
    unused_artifacts = depaginate(
        partial(client.list_artifacts, only_unused=True)
    )

    if not unused_artifacts:
        cli_utils.declare("No unused artifacts found.")
        return

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Found {len(unused_artifacts)} unused artifacts. Do you want to "
            f"delete them?"
        )
        if not confirmation:
            cli_utils.declare("Artifact deletion canceled.")
            return

    for unused_artifact in unused_artifacts:
        try:
            Client().delete_artifact(
                name_id_or_prefix=unused_artifact.id,
                delete_metadata=not only_artifact,
                delete_from_artifact_store=not only_metadata,
            )
        except Exception as e:
            cli_utils.error(str(e))
    cli_utils.declare("All unused artifacts deleted.")
