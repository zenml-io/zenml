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
"""In-process cache of resolved payload values."""

import sys
import threading
from collections import OrderedDict
from concurrent.futures import Future
from typing import Callable, Collection, Dict, List
from uuid import UUID


class PayloadCache:
    """Least recently used cache of payload values, keyed by blob ID.

    Blobs never change, so entries never need to be invalidated. Concurrent
    misses of the same blob wait for a single load, so that, for example,
    the step pods of a run starting together read their snapshot's
    configuration from storage once. A caller waiting for another caller's
    load waits for that whole load, but gets the outcome of its own blobs.
    """

    def __init__(self, max_size: int) -> None:
        """Initializes the cache.

        Args:
            max_size: The maximum memory in bytes taken by the cached values.
                0 disables caching, but concurrent misses are still merged.
        """
        self._max_size = max_size
        self._size = 0
        self._entries: "OrderedDict[UUID, str]" = OrderedDict()
        self._loading: Dict[UUID, "Future[str]"] = {}
        self._lock = threading.Lock()

    def put(self, blob_id: UUID, value: str) -> None:
        """Cache a payload value.

        Args:
            blob_id: The blob holding the value.
            value: The payload value.
        """
        with self._lock:
            self._put_locked(blob_id, value)

    def _put_locked(self, blob_id: UUID, value: str) -> None:
        """Cache a payload value while holding the lock.

        Args:
            blob_id: The blob holding the value.
            value: The payload value.
        """
        # The memory the string takes, which can be several times its UTF-8
        # size.
        size = sys.getsizeof(value)
        if size > self._max_size or blob_id in self._entries:
            return
        while self._size + size > self._max_size:
            _, evicted = self._entries.popitem(last=False)
            self._size -= sys.getsizeof(evicted)
        self._entries[blob_id] = value
        self._size += size

    def get_cached(self, blob_ids: Collection[UUID]) -> Dict[UUID, str]:
        """Get the cached payload values, without loading any.

        Values that another caller is loading are left out, so that nothing
        waits for storage.

        Args:
            blob_ids: The blobs to get.

        Returns:
            The cached values by blob ID.
        """
        values: Dict[UUID, str] = {}
        with self._lock:
            for blob_id in blob_ids:
                if (value := self._entries.get(blob_id)) is not None:
                    self._entries.move_to_end(blob_id)
                    values[blob_id] = value
        return values

    def get_many(
        self,
        blob_ids: Collection[UUID],
        load: Callable[[List[UUID]], Dict[UUID, str]],
    ) -> Dict[UUID, str]:
        """Get payload values, loading the missing ones in one batch.

        Args:
            blob_ids: The blobs to get.
            load: Loads the given blobs.

        Returns:
            The payload values by blob ID.

        Raises:
            BaseException: Any error of this caller's load.
        """
        values: Dict[UUID, str] = {}
        waiting: Dict[UUID, "Future[str]"] = {}
        loading: Dict[UUID, "Future[str]"] = {}
        with self._lock:
            for blob_id in blob_ids:
                if (value := self._entries.get(blob_id)) is not None:
                    self._entries.move_to_end(blob_id)
                    values[blob_id] = value
                elif blob_id in self._loading:
                    waiting[blob_id] = self._loading[blob_id]
                else:
                    loading[blob_id] = self._loading[blob_id] = Future()

        if loading:
            try:
                loaded = load(list(loading))
            except BaseException as e:
                with self._lock:
                    for blob_id, future in loading.items():
                        del self._loading[blob_id]
                        future.set_exception(e)
                raise

            with self._lock:
                for blob_id, future in loading.items():
                    value = loaded[blob_id]
                    self._put_locked(blob_id, value)
                    del self._loading[blob_id]
                    future.set_result(value)
                    values[blob_id] = value

        retry = []
        for blob_id, future in waiting.items():
            try:
                values[blob_id] = future.result()
            except Exception:
                # The other caller's load failed, maybe for another blob of
                # its batch, so this blob gets a load of its own.
                retry.append(blob_id)
        if retry:
            loaded = load(retry)
            with self._lock:
                for blob_id in retry:
                    self._put_locked(blob_id, loaded[blob_id])
            values.update(loaded)
        return values
