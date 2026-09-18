#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Pruning of artifact versions that nothing references.

The SQL store only finds, counts and deletes unused artifact versions.
Deleting their data needs an artifact store, which the store must not load,
so the prune loop lives here and is driven by the server as a maintenance
task or by the client against a local database.
"""

import statistics
import time
from typing import TYPE_CHECKING, Callable, Dict, List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionFilter,
    ArtifactVersionLocation,
    ArtifactVersionPruneRequest,
    ArtifactVersionPruneResponse,
)

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

# Every version in a batch may cost a round trip to the artifact store
# before the batch's metadata goes, so batches stay small enough for an
# interrupted prune to lose little.
ARTIFACT_VERSION_PRUNE_BATCH_SIZE = 500


class ArtifactDataDeleter:
    """Deletes the data of unused artifact versions while they are pruned.

    Every artifact store is loaded once. A version whose artifact store
    cannot be loaded or whose data cannot be deleted is reported and kept, so
    pruning never removes the metadata of data that is still there.
    """

    def __init__(
        self,
        artifact_store_loader: Callable[[UUID], "BaseArtifactStore"],
    ) -> None:
        """Initialize the deleter.

        Args:
            artifact_store_loader: Loads an artifact store by ID. If it
                raises, the versions stored there are kept.
        """
        self._artifact_store_loader = artifact_store_loader
        self._artifact_stores: Dict[UUID, Optional["BaseArtifactStore"]] = {}

    def delete(self, location: ArtifactVersionLocation) -> bool:
        """Delete the data of an unused artifact version if that is possible.

        Args:
            location: Where the data is stored.

        Returns:
            Whether the data was deleted.
        """
        if location.artifact_store_id is None:
            logger.warning(
                f"Keeping artifact version {location.id}: it has no artifact "
                "store."
            )
            return False
        artifact_store = self._get_artifact_store(location.artifact_store_id)
        if artifact_store is None:
            return False
        try:
            if artifact_store.exists(location.uri):
                artifact_store.rmtree(location.uri)
        except Exception as e:
            logger.warning(
                f"Keeping artifact version {location.id} because its data at "
                f"'{location.uri}' could not be deleted: {e}"
            )
            return False
        return True

    def _get_artifact_store(
        self, artifact_store_id: UUID
    ) -> Optional["BaseArtifactStore"]:
        """Load an artifact store once, or remember that it cannot be loaded.

        Args:
            artifact_store_id: The artifact store.

        Returns:
            The artifact store, or None if it cannot be loaded.
        """
        if artifact_store_id not in self._artifact_stores:
            try:
                artifact_store: Optional["BaseArtifactStore"] = (
                    self._artifact_store_loader(artifact_store_id)
                )
            except Exception as e:
                logger.warning(
                    "Keeping the artifact versions stored in artifact store "
                    f"{artifact_store_id}: {e}"
                )
                artifact_store = None
            self._artifact_stores[artifact_store_id] = artifact_store
        return self._artifact_stores[artifact_store_id]


def prune_artifact_versions(
    zen_store: "SqlZenStore",
    prune_request: ArtifactVersionPruneRequest,
    artifact_data_deleter: Optional[ArtifactDataDeleter] = None,
    on_deleted: Optional[Callable[[List[UUID]], None]] = None,
) -> ArtifactVersionPruneResponse:
    """Count or delete the artifact versions of a project that nothing references.

    The versions are walked in ID order in batches. When artifact data is
    deleted, each batch's data goes before its metadata, the same order as
    deleting a single version: a version whose data cannot be deleted keeps
    its metadata and can be retried, and an interrupted prune leaves at most
    one batch of versions without data. A version that is referenced between
    the two steps keeps its metadata while its data is gone, so it is
    reported as an error.

    Args:
        zen_store: The store holding the artifact versions.
        prune_request: Which artifact versions to prune and whether to
            delete them or only count them.
        artifact_data_deleter: Deletes the data of unused artifact versions;
            versions whose data it keeps are kept. Only used, and required,
            when the request asks for data deletion.
        on_deleted: Called with the IDs of every batch of deleted artifact
            versions.

    Returns:
        The number of unused artifact versions for a dry run, otherwise the
        number of artifact versions whose metadata, or for a data-only prune
        whose data, was deleted.

    Raises:
        ValueError: If the request asks for data deletion without a way to
            delete it.
    """
    if not prune_request.apply:
        return ArtifactVersionPruneResponse(
            artifact_version_count=zen_store.count_artifact_versions(
                ArtifactVersionFilter(
                    project=prune_request.project, only_unused=True
                )
            )
        )
    if not prune_request.delete_from_artifact_store:
        artifact_data_deleter = None
    elif artifact_data_deleter is None:
        raise ValueError("Deleting artifact data requires a way to delete it.")

    start = time.monotonic()
    pruned_count = 0
    after: Optional[UUID] = None
    while locations := zen_store.list_unused_artifact_version_locations(
        prune_request.project,
        after=after,
        limit=ARTIFACT_VERSION_PRUNE_BATCH_SIZE,
    ):
        after = locations[-1].id
        if artifact_data_deleter:
            locations = _delete_data(artifact_data_deleter, locations)
        if not prune_request.delete_metadata:
            pruned_count += len(locations)
            continue
        deleted = zen_store.delete_unused_artifact_versions(
            [location.id for location in locations]
        )
        if artifact_data_deleter and len(deleted) < len(locations):
            deleted_ids = set(deleted)
            kept = ", ".join(
                str(location.id)
                for location in locations
                if location.id not in deleted_ids
            )
            logger.error(
                f"Artifact version(s) {kept} were referenced after their "
                "data was deleted and were kept. Their data is gone."
            )
        if on_deleted and deleted:
            on_deleted(deleted)
        pruned_count += len(deleted)

    if prune_request.delete_metadata and not prune_request.only_versions:
        zen_store.delete_artifacts_without_versions(prune_request.project)
    logger.info(
        f"Pruned {pruned_count} artifact version(s) of project "
        f"{prune_request.project} in {time.monotonic() - start:.2f}s."
    )
    return ArtifactVersionPruneResponse(artifact_version_count=pruned_count)


def _delete_data(
    artifact_data_deleter: ArtifactDataDeleter,
    locations: List[ArtifactVersionLocation],
) -> List[ArtifactVersionLocation]:
    """Delete the data of a batch of artifact versions and log how long it took.

    Data is deleted one version at a time, usually over the network, and
    that is expected to dominate the prune, so every batch reports the
    per-version duration distribution.

    Args:
        artifact_data_deleter: Deletes the data of one artifact version.
        locations: The artifact versions whose data is deleted.

    Returns:
        The artifact versions whose data was deleted.
    """
    deleted: List[ArtifactVersionLocation] = []
    seconds: List[float] = []
    for location in locations:
        start = time.monotonic()
        data_deleted = artifact_data_deleter.delete(location)
        seconds.append(time.monotonic() - start)
        if data_deleted:
            deleted.append(location)
    logger.info(
        f"Deleting the data of {len(locations)} artifact version(s) took "
        f"{sum(seconds):.2f}s (per version: min {min(seconds):.3f}s, median "
        f"{statistics.median(seconds):.3f}s, mean "
        f"{statistics.mean(seconds):.3f}s, max {max(seconds):.3f}s)."
    )
    return deleted
