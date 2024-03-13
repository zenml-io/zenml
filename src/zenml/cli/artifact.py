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
from typing import Any, Dict, List, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import ArtifactFilter, ArtifactVersionFilter
from zenml.models.v2.core.artifact import ArtifactResponse
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.utils.pagination_utils import depaginate

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def artifact() -> None:
    """Commands for interacting with artifacts."""


@cli_utils.list_options(ArtifactFilter)
@artifact.command("list", help="List all artifacts.")
def list_artifacts(**kwargs: Any) -> None:
    """List all artifacts.

    Args:
        **kwargs: Keyword arguments to filter artifacts by.
    """
    artifacts = Client().list_artifacts(**kwargs)

    if not artifacts:
        cli_utils.declare("No artifacts found.")
        return

    to_print = []
    for artifact in artifacts:
        to_print.append(_artifact_to_print(artifact))

    cli_utils.print_table(to_print)


@artifact.command("update", help="Update an artifact.")
@click.argument("artifact_name_or_id")
@click.option(
    "--name",
    "-n",
    type=str,
    help="New name of the artifact.",
)
@click.option(
    "--tag",
    "-t",
    type=str,
    multiple=True,
    help="Tags to add to the artifact.",
)
@click.option(
    "--remove-tag",
    "-r",
    type=str,
    multiple=True,
    help="Tags to remove from the artifact.",
)
def update_artifact(
    artifact_name_or_id: str,
    name: Optional[str] = None,
    tag: Optional[List[str]] = None,
    remove_tag: Optional[List[str]] = None,
) -> None:
    """Update an artifact by ID or name.

    Usage example:
    ```
    zenml artifact update <NAME> -n <NEW_NAME> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
    ```

    Args:
        artifact_name_or_id: Name or ID of the artifact to update.
        name: New name of the artifact.
        tag: New tags of the artifact.
        remove_tag: Tags to remove from the artifact.
    """
    try:
        artifact = Client().update_artifact(
            name_id_or_prefix=artifact_name_or_id,
            new_name=name,
            add_tags=tag,
            remove_tags=remove_tag,
        )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Artifact '{artifact.id}' updated.")


@artifact.group()
def version() -> None:
    """Commands for interacting with artifact versions."""


@cli_utils.list_options(ArtifactVersionFilter)
@version.command("list", help="List all artifact versions.")
def list_artifact_versions(**kwargs: Any) -> None:
    """List all artifact versions.

    Args:
        **kwargs: Keyword arguments to filter artifact versions by.
    """
    artifact_versions = Client().list_artifact_versions(**kwargs)

    if not artifact_versions:
        cli_utils.declare("No artifact versions found.")
        return

    to_print = []
    for artifact_version in artifact_versions:
        to_print.append(_artifact_version_to_print(artifact_version))

    cli_utils.print_table(to_print)


@version.command("update", help="Update an artifact version.")
@click.argument("name_id_or_prefix")
@click.option(
    "--version",
    "-v",
    type=str,
    help=(
        "The version of the artifact to get. Only used if "
        "`name_id_or_prefix` is the name of the artifact. If not specified, "
        "the latest version is returned."
    ),
)
@click.option(
    "--tag",
    "-t",
    type=str,
    multiple=True,
    help="Tags to add to the artifact version.",
)
@click.option(
    "--remove-tag",
    "-r",
    type=str,
    multiple=True,
    help="Tags to remove from the artifact version.",
)
def update_artifact_version(
    name_id_or_prefix: str,
    version: Optional[str] = None,
    tag: Optional[List[str]] = None,
    remove_tag: Optional[List[str]] = None,
) -> None:
    """Update an artifact version by ID or artifact name.

    Usage example:
    ```
    zenml artifact version update <NAME> -v <VERSION> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
    ```

    Args:
        name_id_or_prefix: Either the ID of the artifact version or the name of
            the artifact.
        version: The version of the artifact to get. Only used if
            `name_id_or_prefix` is the name of the artifact. If not specified,
            the latest version is returned.
        tag: Tags to add to the artifact version.
        remove_tag: Tags to remove from the artifact version.
    """
    try:
        artifact_version = Client().update_artifact_version(
            name_id_or_prefix=name_id_or_prefix,
            version=version,
            add_tags=tag,
            remove_tags=remove_tag,
        )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Artifact version '{artifact_version.id}' updated.")


@artifact.command(
    "prune",
    help=(
        "Delete all unused artifacts and artifact versions that are no longer "
        "referenced by any pipeline runs."
    ),
)
@click.option(
    "--only-artifact",
    "-a",
    is_flag=True,
    help=(
        "Only delete the actual artifact object from the artifact store but "
        "keep the metadata."
    ),
)
@click.option(
    "--only-metadata",
    "-m",
    is_flag=True,
    help=(
        "Only delete metadata and not the actual artifact object stored in "
        "the artifact store."
    ),
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
    """Delete all unused artifacts and artifact versions.

    Unused artifact versions are those that are no longer referenced by any
    pipeline runs. Similarly, unused artifacts are those that no longer have
    any used artifact versions.

    Args:
        only_artifact: If set, only delete the actual artifact object from the
            artifact store but keep the metadata.
        only_metadata: If set, only delete metadata and not the actual artifact
            objects stored in the artifact store.
        yes: If set, don't ask for confirmation.
    """
    client = Client()
    unused_artifact_versions = depaginate(
        partial(client.list_artifact_versions, only_unused=True)
    )

    if not unused_artifact_versions:
        cli_utils.declare("No unused artifact versions found.")
        return

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Found {len(unused_artifact_versions)} unused artifact versions. "
            f"Do you want to delete them?"
        )
        if not confirmation:
            cli_utils.declare("Artifact deletion canceled.")
            return

    for unused_artifact_version in unused_artifact_versions:
        try:
            Client().delete_artifact_version(
                name_id_or_prefix=unused_artifact_version.id,
                delete_metadata=not only_artifact,
                delete_from_artifact_store=not only_metadata,
            )
            unused_artifact = unused_artifact_version.artifact
            if not unused_artifact.versions and not only_artifact:
                Client().delete_artifact(unused_artifact.id)

        except Exception as e:
            cli_utils.error(str(e))
    cli_utils.declare("All unused artifacts and artifact versions deleted.")


def _artifact_version_to_print(
    artifact_version: ArtifactVersionResponse,
) -> Dict[str, Any]:
    return {
        "id": artifact_version.id,
        "name": artifact_version.artifact.name,
        "version": artifact_version.version,
        "uri": artifact_version.uri,
        "type": artifact_version.type,
        "materializer": artifact_version.materializer,
        "data_type": artifact_version.data_type,
        "tags": [t.name for t in artifact_version.tags],
    }


def _artifact_to_print(
    artifact_version: ArtifactResponse,
) -> Dict[str, Any]:
    return {
        "id": artifact_version.id,
        "name": artifact_version.name,
        "tags": [t.name for t in artifact_version.tags],
    }
