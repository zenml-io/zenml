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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Byte-bounded cache of decoded, immutable archive objects."""

import threading
from collections import OrderedDict
from typing import Callable, Dict, Generic, Tuple, TypeVar

T = TypeVar("T")


class ExecutionArchiveCache(Generic[T]):
    """Thread-safe LRU cache keyed by object digest.

    Objects are immutable, so an entry never goes stale. Entries are weighed
    by the size the loader reports, which is the decoded size of the object,
    not its compressed size on the store. Concurrent requests for the same
    object share one load, so a burst of reads of a large cold family
    decodes it once.
    """

    def __init__(self, max_bytes: int) -> None:
        """Initialize the cache.

        Args:
            max_bytes: Maximum total weight of the cached entries.

        Raises:
            ValueError: If the limit is not positive.
        """
        if max_bytes <= 0:
            raise ValueError("The archive cache size must be positive.")
        self._max_bytes = max_bytes
        self._size = 0
        self._entries: "OrderedDict[str, Tuple[int, T]]" = OrderedDict()
        self._lock = threading.Lock()
        self._loading: Dict[str, threading.Lock] = {}

    def get_or_load(
        self, digest: str, loader: Callable[[], Tuple[T, int]]
    ) -> T:
        """Return the cached value or load, weigh and cache it.

        Args:
            digest: The object digest.
            loader: Loads the object and returns it with its weight.

        Returns:
            The decoded object.
        """
        cached = self._get(digest)
        if cached is not None:
            return cached
        with self._lock:
            load_lock = self._loading.setdefault(digest, threading.Lock())
        with load_lock:
            cached = self._get(digest)
            if cached is not None:
                return cached
            try:
                value, weight = loader()
            finally:
                with self._lock:
                    self._loading.pop(digest, None)
            with self._lock:
                if weight <= self._max_bytes:
                    self._entries[digest] = (weight, value)
                    self._size += weight
                    while self._size > self._max_bytes:
                        _, (evicted, _) = self._entries.popitem(last=False)
                        self._size -= evicted
            return value

    def _get(self, digest: str) -> "T | None":
        with self._lock:
            entry = self._entries.get(digest)
            if entry is None:
                return None
            self._entries.move_to_end(digest)
            return entry[1]
