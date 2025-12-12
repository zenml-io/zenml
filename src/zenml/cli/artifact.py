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

import threading
from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ThreadPoolExecutor,
    wait,
)
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import OutputFormat, list_options
from zenml.client import Client
from zenml.console import console
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


@artifact.command("list", help="List all artifacts.")
@list_options(
    ArtifactFilter,
    default_columns=["id", "name", "latest_version_name", "tags"],
)
def list_artifacts(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List all artifacts.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter artifacts by.
    """
    with console.status("Listing artifacts...\n"):
        artifacts = Client().list_artifacts(**kwargs)

    cli_utils.print_page(
        artifacts, columns, output_format, empty_message="No artifacts found."
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
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Artifact '{artifact.id}' updated.")


@artifact.group()
def version() -> None:
    """Commands for interacting with artifact versions."""


@version.command("list", help="List all artifact versions.")
@list_options(
    ArtifactVersionFilter,
    default_columns=["id", "artifact", "version", "type"],
)
def list_artifact_versions(
    columns: str, output_format: OutputFormat, **kwargs: Any
) -> None:
    """List all artifact versions.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter artifact versions by.
    """
    with console.status("Listing artifact versions...\n"):
        artifact_versions = Client().list_artifact_versions(**kwargs)

    cli_utils.print_page(
        artifact_versions,
        columns,
        output_format,
        empty_message="No artifact versions found.",
    )


@version.command("describe", help="Show details about an artifact version.")
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
def describe_artifact_version(
    name_id_or_prefix: str,
    version: Optional[str] = None,
) -> None:
    """Show details about an artifact version.

    Usage example:
    ```
    zenml artifact version describe <NAME> -v <VERSION>
    zenml artifact version describe <ARTIFACT_VERSION_ID>
    ```

    Args:
        name_id_or_prefix: Either the ID of the artifact version or the name of
            the artifact.
        version: The version of the artifact to get. Only used if
            `name_id_or_prefix` is the name of the artifact. If not specified,
            the latest version is returned.
    """
    client = Client()
    try:
        artifact_version = client.get_artifact_version(
            name_id_or_prefix=name_id_or_prefix,
            version=version,
        )
    except (KeyError, ValueError) as e:
        cli_utils.exception(e)
    else:
        cli_utils.print_pydantic_model(
            title=f"Artifact version '{artifact_version.artifact.name}' (version: {artifact_version.version})",
            model=artifact_version,
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
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Artifact version '{artifact_version.id}' updated.")


# Thread-local storage for Client instances used in parallel deletion
_thread_local = threading.local()


def _get_thread_local_client() -> Client:
    """Get or create a thread-local Client instance."""
    if not hasattr(_thread_local, "client"):
        _thread_local.client = Client()
    client: Client = _thread_local.client
    return client


@dataclass(frozen=True)
class _PruneTarget:
    """Target for artifact version deletion."""

    artifact_version_id: UUID
    artifact_id: UUID


def _delete_artifact_version_target(
    target: _PruneTarget,
    delete_metadata: bool,
    delete_from_artifact_store: bool,
) -> _PruneTarget:
    """Delete an artifact version.

    Args:
        target: The target containing artifact version and artifact IDs.
        delete_metadata: Whether to delete the metadata.
        delete_from_artifact_store: Whether to delete from artifact store.

    Returns:
        The target for downstream artifact cleanup tracking.
    """
    client = _get_thread_local_client()
    client.delete_artifact_version(
        name_id_or_prefix=target.artifact_version_id,
        delete_metadata=delete_metadata,
        delete_from_artifact_store=delete_from_artifact_store,
    )
    return target


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
@click.option(
    "--threads",
    "-t",
    type=click.IntRange(1, None),
    default=1,
    show_default=True,
    help="Number of threads for parallel deletion of artifact versions.",
)
def prune_artifacts(
    only_artifact: bool = False,
    only_metadata: bool = False,
    yes: bool = False,
    ignore_errors: bool = False,
    threads: int = 1,
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
        threads: Number of parallel threads for artifact version deletion.
    """
    if only_artifact and only_metadata:
        cli_utils.error(
            "Cannot use both `--only-artifact` and `--only-metadata` together."
        )

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

    targets: List[_PruneTarget] = [
        _PruneTarget(
            artifact_version_id=unused_artifact_version.id,
            artifact_id=unused_artifact_version.artifact.id,
        )
        for unused_artifact_version in unused_artifact_versions
    ]
    artifact_ids: Set[UUID] = {t.artifact_id for t in targets}

    total = len(targets)
    completed = 0
    failed_deletions = 0
    delete_metadata = not only_artifact
    delete_from_artifact_store = not only_metadata

    future_to_target: Dict[Future[_PruneTarget], _PruneTarget] = {}
    in_flight: Set[Future[_PruneTarget]] = set()
    targets_iter = iter(targets)

    with console.status(
        f"Deleting unused artifact versions... ({completed}/{total})"
    ) as status:
        with ThreadPoolExecutor(max_workers=threads) as executor:

            def submit_next() -> None:
                try:
                    target = next(targets_iter)
                except StopIteration:
                    return

                future: Future[_PruneTarget] = executor.submit(
                    _delete_artifact_version_target,
                    target=target,
                    delete_metadata=delete_metadata,
                    delete_from_artifact_store=delete_from_artifact_store,
                )
                future_to_target[future] = target
                in_flight.add(future)

            for _ in range(min(threads, total)):
                submit_next()

            while in_flight:
                done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                for future in done:
                    in_flight.remove(future)
                    target = future_to_target.pop(future)

                    try:
                        future.result()
                    except Exception as e:
                        if ignore_errors:
                            cli_utils.warning(
                                f"Failed to delete artifact version {target.artifact_version_id}: {str(e)}"
                            )
                            failed_deletions += 1
                        else:
                            cli_utils.error(
                                f"Failed to delete artifact version {target.artifact_version_id}: {str(e)}"
                            )

                    completed += 1
                    status.update(
                        f"Deleting unused artifact versions... ({completed}/{total})"
                    )
                    submit_next()

    if not only_artifact:
        for artifact_id in artifact_ids:
            try:
                versions_page = client.list_artifact_versions(
                    artifact=artifact_id, size=1
                )

                has_versions = versions_page.total > 0

                if not has_versions:
                    client.delete_artifact(artifact_id)
            except Exception as e:
                if ignore_errors:
                    cli_utils.warning(
                        f"Failed to delete artifact {artifact_id}: {str(e)}"
                    )
                    failed_deletions += 1
                else:
                    cli_utils.error(
                        f"Failed to delete artifact {artifact_id}: {str(e)}"
                    )

    if failed_deletions > 0:
        cli_utils.warning(
            f"Pruning completed with {failed_deletions} error(s). "
            "Some artifacts may not have been deleted."
        )
    else:
        cli_utils.declare(
            "All unused artifacts and artifact versions deleted."
        )


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
