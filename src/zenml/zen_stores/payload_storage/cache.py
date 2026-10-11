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
"""In-process cache of loaded payload values."""

import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, Collection, Dict, List
from uuid import UUID

from zenml.exceptions import PayloadStorageUnavailableError


class PayloadCache:
    """Least recently used cache of payload values, keyed by blob ID.

    Blobs never change, so entries never need to be invalidated. Concurrent
    misses of the same blob wait for a single load, so that, for example,
    the step pods of a run starting together read their snapshot's
    configuration from storage once. A caller waiting for another caller's
    load waits for it until its own deadline, and gets the outcome of its own
    blobs.
    """

    def __init__(self, max_bytes: int) -> None:
        """Initializes the cache.

        Args:
            max_bytes: The maximum memory in bytes taken by the cached values.
                0 disables caching, but concurrent misses are still merged.
        """
        self._max_bytes = max_bytes
        self._size_bytes = 0
        self._entries: "OrderedDict[UUID, str]" = OrderedDict()
        self._in_flight_loads: Dict[UUID, "Future[str]"] = {}
        # Reentrant, so that loads can cache their values with `put` while
        # they hold it.
        self._lock = threading.RLock()

    def put(self, blob_id: UUID, value: str) -> None:
        """Cache a payload value.

        Args:
            blob_id: The blob holding the value.
            value: The payload value.
        """
        # The memory the string takes, which can be several times its UTF-8
        # size.
        size = sys.getsizeof(value)
        with self._lock:
            if size > self._max_bytes or blob_id in self._entries:
                return
            while self._size_bytes + size > self._max_bytes:
                _, evicted = self._entries.popitem(last=False)
                self._size_bytes -= sys.getsizeof(evicted)
            self._entries[blob_id] = value
            self._size_bytes += size

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

    def get_or_load(
        self,
        blob_ids: Collection[UUID],
        loader: Callable[[List[UUID], float], Dict[UUID, str]],
        deadline: float,
    ) -> Dict[UUID, str]:
        """Get payload values, loading the missing ones in one batch.

        Args:
            blob_ids: The blobs to get.
            loader: Loads the given blobs by the given deadline.
            deadline: The `time.monotonic()` by which the values are loaded,
                including waits for other callers' loads and loads again.

        Returns:
            The payload values by blob ID.
        """
        return self._get_or_load(
            blob_ids, loader, deadline, retry_failed_waits=True
        )

    def _get_or_load(
        self,
        blob_ids: Collection[UUID],
        loader: Callable[[List[UUID], float], Dict[UUID, str]],
        deadline: float,
        retry_failed_waits: bool,
    ) -> Dict[UUID, str]:
        """Get payload values, loading the missing ones in one batch.

        Args:
            blob_ids: The blobs to get.
            loader: Loads the given blobs by the given deadline.
            deadline: The `time.monotonic()` by which the values are loaded.
            retry_failed_waits: Whether blobs of another caller's load that
                failed for good are loaded again.

        Returns:
            The payload values by blob ID.

        Raises:
            BaseException: Any error of this caller's load.
            PayloadStorageUnavailableError: If the deadline passed while this
                caller waited for the load of another one, or storage failed
                that load.
            Exception: Any other error of another caller's load that this one
                waited for, once it is not loaded again.
        """
        values: Dict[UUID, str] = {}
        waiting: Dict[UUID, "Future[str]"] = {}
        loading: Dict[UUID, "Future[str]"] = {}
        with self._lock:
            for blob_id in blob_ids:
                if (value := self._entries.get(blob_id)) is not None:
                    self._entries.move_to_end(blob_id)
                    values[blob_id] = value
                elif blob_id in self._in_flight_loads:
                    waiting[blob_id] = self._in_flight_loads[blob_id]
                else:
                    loading[blob_id] = self._in_flight_loads[blob_id] = (
                        Future()
                    )

        if loading:
            try:
                loaded = loader(list(loading), deadline)
            except BaseException as e:
                with self._lock:
                    for blob_id, future in loading.items():
                        del self._in_flight_loads[blob_id]
                        future.set_exception(e)
                raise

            with self._lock:
                for blob_id, future in loading.items():
                    value = loaded[blob_id]
                    self.put(blob_id, value)
                    del self._in_flight_loads[blob_id]
                    future.set_result(value)
                    values[blob_id] = value

        retry = []
        for blob_id, future in waiting.items():
            try:
                values[blob_id] = future.result(
                    timeout=max(deadline - time.monotonic(), 0)
                )
            except FutureTimeoutError:
                raise PayloadStorageUnavailableError(
                    "Execution payload storage did not load the payloads in "
                    "time."
                ) from None
            except PayloadStorageUnavailableError as e:
                # Storage just failed this load, so loading again would most
                # likely hold this request until its deadline and fail too.
                raise PayloadStorageUnavailableError(str(e)) from e
            except Exception:
                if not retry_failed_waits:
                    raise
                # The other caller's load failed for good, maybe because of
                # another blob of its batch, so these blobs are loaded again,
                # merged with any other caller that needs them.
                retry.append(blob_id)
        if retry:
            values.update(
                self._get_or_load(
                    retry, loader, deadline, retry_failed_waits=False
                )
            )
        return values
