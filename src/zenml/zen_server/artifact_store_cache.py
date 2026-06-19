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
"""Bounded LRU cache of artifact store instances."""

import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple, cast
from uuid import UUID

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.models import ComponentResponse

logger = get_logger(__name__)

DEFAULT_ARTIFACT_STORE_CACHE_SIZE = 20
DEFAULT_ARTIFACT_STORE_CACHE_TTL = 3600.0


class _CacheEntry(NamedTuple):
    """Artifact store cache entry."""

    store: "BaseArtifactStore"
    updated: datetime
    inserted_at: float


class ArtifactStoreCache:
    """Bounded LRU cache of artifact store instances."""

    def __init__(
        self,
        max_size: int = DEFAULT_ARTIFACT_STORE_CACHE_SIZE,
        ttl: float = DEFAULT_ARTIFACT_STORE_CACHE_TTL,
    ) -> None:
        """Initialize the cache.

        Args:
            max_size: Maximum number of artifact store instances to retain.
            ttl: Seconds after which a cached instance is rebuilt.
        """
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()
        self._entries: "OrderedDict[UUID, _CacheEntry]" = OrderedDict()

    def get_or_create(self, model: "ComponentResponse") -> "BaseArtifactStore":
        """Return a cached artifact store for the model, building it if needed.

        Args:
            model: The artifact store component model.

        Returns:
            A cached or freshly built artifact store instance.
        """
        updated = self._effective_updated(model)

        with self._lock:
            entry = self._entries.get(model.id)
            if entry is not None and not self._is_expired(entry, updated):
                self._entries.move_to_end(model.id)
                return entry.store

        # Instantiate outside the lock
        store = self._instantiate(model)

        with self._lock:
            entry = self._entries.get(model.id)
            if entry is not None and not self._is_expired(entry, updated):
                # Another thread instantiated the same store concurrently. We
                # throw ours away and use the existing one.
                self._safe_cleanup(store)
                self._entries.move_to_end(model.id)
                return entry.store

            # Replace the stale entry without cleaning it up. A concurrent
            # request may still hold and use the old instance, and cleanup()
            # closes its filesystem. The orphaned instance is reclaimed by GC.
            self._entries.pop(model.id, None)
            self._entries[model.id] = _CacheEntry(
                store, updated, time.monotonic()
            )
            self._maybe_evict()
            return store

    def clear(self) -> None:
        """Cleanup and drop all cached artifact stores."""
        with self._lock:
            for entry in self._entries.values():
                self._safe_cleanup(entry.store)
            self._entries.clear()

    def _effective_updated(self, model: "ComponentResponse") -> datetime:
        """The most recent of the component and its connector update timestamps.

        Args:
            model: The artifact store component model.

        Returns:
            The most recent update timestamp of the component and its connector.
        """
        if connector := model.connector:
            return max(model.updated, connector.updated)
        return model.updated

    def _is_expired(self, entry: _CacheEntry, updated: datetime) -> bool:
        """Whether a cache entry is expired.

        Args:
            entry: The cached entry.
            updated: The effective update timestamp of the current model.

        Returns:
            Whether the entry is expired.
        """
        return (
            entry.updated != updated
            or (time.monotonic() - entry.inserted_at) > self._ttl
        )

    def _instantiate(self, model: "ComponentResponse") -> "BaseArtifactStore":
        """Instantiate an artifact store from a component model.

        Args:
            model: The artifact store component model.

        Returns:
            The instantiated artifact store.
        """
        from zenml.stack import StackComponent

        return cast("BaseArtifactStore", StackComponent.from_model(model))

    def _maybe_evict(self) -> None:
        """Evict least-recently-used entries if the cache is full."""
        # Evicted instances are dropped without cleanup. A concurrent request
        # may still hold one, and cleanup() closes its filesystem. GC reclaims
        # the orphaned instance once no request references it.
        while len(self._entries) > self._max_size:
            self._entries.popitem(last=False)

    @staticmethod
    def _safe_cleanup(store: "BaseArtifactStore") -> None:
        """Run an artifact store cleanup, swallowing errors.

        Args:
            store: The artifact store to clean up.
        """
        try:
            store.cleanup()
        except Exception as e:
            logger.debug("Error cleaning up cached artifact store: %s", e)
