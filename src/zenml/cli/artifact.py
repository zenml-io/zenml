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

from typing import Any, Dict, List, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    enhanced_list_options,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import (
    ArtifactFilter,
    ArtifactResponse,
    ArtifactVersionFilter,
    ArtifactVersionResponse,
)
from zenml.utils.pagination_utils import depaginate

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def artifact() -> None:
    """Commands for interacting with artifacts."""


@enhanced_list_options(
    ArtifactFilter,
    default_columns=["id", "name", "latest_version_name", "user", "created"],
)
@artifact.command("list", help="List all artifacts.")
def list_artifacts(**kwargs: Any) -> None:
    """List all artifacts.

    Args:
        **kwargs: Keyword arguments to filter artifacts by.
    """
    # Extract table options from kwargs
    table_kwargs = cli_utils.extract_table_options(kwargs)

    with console.status("Listing artifacts..."):
        artifacts = Client().list_artifacts(**kwargs)

    if not artifacts:
        cli_utils.declare("No artifacts found.")
        return

    # Prepare data based on output format
    output_format = (
        table_kwargs.get("output") or cli_utils.get_default_output_format()
    )

    def enrichment_func(
        item: ArtifactResponse, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich the artifact data with the latest version name and id.

        Args:
            item: The artifact response.
            result: The result dictionary.

        Returns:
            The enriched result dictionary.
        """
        result.update(
            {
                "latest_version_name": item.latest_version_name,
                "latest_version_id": item.latest_version_id,
            }
        )
        return result

    artifact_data = cli_utils.prepare_data_from_responses(
        artifacts.items, output_format, enrichment_func=enrichment_func
    )

    # Handle table output with enhanced system and pagination
    cli_utils.handle_table_output(
        artifact_data, page=artifacts, **table_kwargs
    )


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


@enhanced_list_options(
    ArtifactVersionFilter,
    default_columns=["id", "name", "version", "type", "user", "created"],
)
@version.command("list", help="List all artifact versions.")
def list_artifact_versions(**kwargs: Any) -> None:
    """List all artifact versions.

    Args:
        **kwargs: Keyword arguments to filter artifact versions by.
    """
    # Extract table options from kwargs
    table_kwargs = cli_utils.extract_table_options(kwargs)

    with console.status("Listing artifact versions..."):
        artifact_versions = Client().list_artifact_versions(**kwargs)

    if not artifact_versions:
        cli_utils.declare("No artifact versions found.")
        return

    # Prepare data based on output format
    output_format = (
        table_kwargs.get("output") or cli_utils.get_default_output_format()
    )

    def enrichment_func(
        item: ArtifactVersionResponse, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich the artifact version data with the artifact name.

        Args:
            item: The artifact version response.
            result: The result dictionary.

        Returns:
            The enriched result dictionary.
        """
        result.update({"name": item.artifact.name})
        return result

    artifact_version_data = cli_utils.prepare_data_from_responses(
        artifact_versions.items, output_format, enrichment_func=enrichment_func
    )

    # Handle table output with enhanced system and pagination
    cli_utils.handle_table_output(
        artifact_version_data, page=artifact_versions, **table_kwargs
    )


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
@click.option(
    "--ignore-errors",
    "-i",
    is_flag=True,
    help="Ignore errors and continue with the next artifact version.",
)
def prune_artifacts(
    only_artifact: bool = False,
    only_metadata: bool = False,
    yes: bool = False,
    ignore_errors: bool = False,
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
        ignore_errors: If set, ignore errors and continue with the next
            artifact version.
    """
    client = Client()
    unused_artifact_versions = depaginate(
        client.list_artifact_versions, only_unused=True
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
            if ignore_errors:
                cli_utils.warning(
                    f"Failed to delete artifact version {unused_artifact_version.id}: {str(e)}"
                )
            else:
                cli_utils.error(
                    f"Failed to delete artifact version {unused_artifact_version.id}: {str(e)}"
                )
    cli_utils.declare("All unused artifacts and artifact versions deleted.")
