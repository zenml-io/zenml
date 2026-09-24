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
"""Boundary between artifact-version pruning in the database and outside it.

`SqlZenStore.prune_artifact_versions` owns the whole database side of
pruning. Everything outside the database, such as deleting artifact data or
server authorization records, goes through one `ArtifactPruneHandler`, which
the store calls only while no SQL transaction is open.
"""

import statistics
import time
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Tuple,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore

logger = get_logger(__name__)


class ArtifactDataReference(BaseModel):
    """Where the data of an artifact version is stored.

    The SQL store passes these values through without acting on them; a
    prune handler decides what they mean.
    """

    model_config = ConfigDict(frozen=True)

    uri: str
    storage_id: Optional[UUID]


class ArtifactPruneCandidate(BaseModel):
    """An unused artifact version selected for pruning."""

    model_config = ConfigDict(frozen=True)

    artifact_version_id: UUID
    data_reference: ArtifactDataReference


class ArtifactPruneBatch(BaseModel):
    """A batch of unused artifact versions presented to the prune handler."""

    model_config = ConfigDict(frozen=True)

    candidates: Tuple[ArtifactPruneCandidate, ...]

    @property
    def artifact_version_ids(self) -> FrozenSet[UUID]:
        """The IDs of all artifact versions in the batch.

        Returns:
            The artifact version IDs.
        """
        return frozenset(
            candidate.artifact_version_id for candidate in self.candidates
        )


class ArtifactPrunePreparation(BaseModel):
    """The artifact versions of a batch that may be deleted from the database.

    Versions left out stay in the database and a later prune retries them;
    the handler reports why it left them out.
    """

    model_config = ConfigDict(frozen=True)

    prepared_artifact_version_ids: FrozenSet[UUID]


class ArtifactPruneDatabaseChanges(BaseModel):
    """Database changes of a prune that have already been committed.

    `retained_artifact_version_ids` holds prepared versions that the store
    kept because something referenced them before they were deleted.
    """

    model_config = ConfigDict(frozen=True)

    deleted_artifact_version_ids: FrozenSet[UUID] = frozenset()
    retained_artifact_version_ids: FrozenSet[UUID] = frozenset()
    deleted_artifact_ids: FrozenSet[UUID] = frozenset()


class ArtifactPruneHandler(ABC):
    """Performs every effect of artifact pruning outside the SQL database.

    Implementations must not read or write the ZenML database.
    """

    @abstractmethod
    def prepare_batch(
        self, batch: ArtifactPruneBatch
    ) -> ArtifactPrunePreparation:
        """Do the external work that has to happen before database deletion.

        Called without an open SQL transaction. Raising leaves the whole
        batch in the database and aborts the prune.

        Args:
            batch: Unused artifact versions selected by the store.

        Returns:
            The artifact versions of the batch that may be deleted.
        """

    @abstractmethod
    def database_changes_committed(
        self, changes: ArtifactPruneDatabaseChanges
    ) -> None:
        """Do the external work that follows committed database changes.

        Called without an open SQL transaction. The changes cannot be rolled
        back if this fails, so implementations must be idempotent.

        Args:
            changes: The committed database changes.
        """


class ArtifactStorePruneHandler(ArtifactPruneHandler):
    """Prune handler that deletes artifact data from artifact stores.

    Every artifact store is loaded once. A version whose artifact store
    cannot be loaded or whose data cannot be deleted is kept, so pruning
    never removes the metadata of data that is still there.
    """

    def __init__(
        self,
        *,
        delete_external_data: bool,
        artifact_store_loader: Callable[[UUID], "BaseArtifactStore"],
    ) -> None:
        """Initialize the handler.

        Args:
            delete_external_data: Whether to delete the data of the pruned
                artifact versions.
            artifact_store_loader: Loads an artifact store by ID. If it
                raises, the versions stored there are kept.
        """
        self._delete_external_data = delete_external_data
        self._artifact_store_loader = artifact_store_loader
        self._artifact_stores: Dict[UUID, Optional["BaseArtifactStore"]] = {}

    def prepare_batch(
        self, batch: ArtifactPruneBatch
    ) -> ArtifactPrunePreparation:
        """Delete the data of a batch of unused artifact versions.

        Data is deleted one version at a time, usually over the network, and
        that is expected to dominate the prune, so every batch reports the
        per-version duration distribution.

        Args:
            batch: Unused artifact versions selected by the store.

        Returns:
            The artifact versions whose data is gone.
        """
        if not self._delete_external_data:
            return ArtifactPrunePreparation(
                prepared_artifact_version_ids=batch.artifact_version_ids
            )

        prepared = set()
        seconds: List[float] = []
        for candidate in batch.candidates:
            start = time.monotonic()
            if self._delete_data(candidate):
                prepared.add(candidate.artifact_version_id)
            seconds.append(time.monotonic() - start)
        if seconds:
            logger.info(
                f"Deleting the data of {len(seconds)} artifact version(s) "
                f"took {sum(seconds):.2f}s (per version: min "
                f"{min(seconds):.3f}s, median "
                f"{statistics.median(seconds):.3f}s, mean "
                f"{statistics.mean(seconds):.3f}s, max {max(seconds):.3f}s)."
            )
        return ArtifactPrunePreparation(
            prepared_artifact_version_ids=frozenset(prepared)
        )

    def database_changes_committed(
        self, changes: ArtifactPruneDatabaseChanges
    ) -> None:
        """Report artifact versions that were kept after their data was deleted.

        Args:
            changes: The committed database changes.
        """
        if (
            self._delete_external_data
            and changes.retained_artifact_version_ids
        ):
            kept = ", ".join(
                sorted(map(str, changes.retained_artifact_version_ids))
            )
            logger.error(
                f"Artifact version(s) {kept} were referenced after their "
                "data was deleted and were kept. Their data is gone."
            )

    def _delete_data(self, candidate: ArtifactPruneCandidate) -> bool:
        """Delete the data of an unused artifact version if that is possible.

        Args:
            candidate: The artifact version.

        Returns:
            Whether the data is gone.
        """
        reference = candidate.data_reference
        if reference.storage_id is None:
            logger.warning(
                f"Keeping artifact version {candidate.artifact_version_id}: "
                "it has no artifact store."
            )
            return False
        artifact_store = self._get_artifact_store(reference.storage_id)
        if artifact_store is None:
            return False
        try:
            if artifact_store.exists(reference.uri):
                artifact_store.rmtree(reference.uri)
        except Exception as e:
            logger.warning(
                f"Keeping artifact version {candidate.artifact_version_id} "
                f"because its data at '{reference.uri}' could not be "
                f"deleted: {e}"
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
