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
"""A cache of server facts, shared by the tool calls of one process."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from zenml_mcp.client import ZenMLUnavailable

V = TypeVar("V")

# A load that takes longer fails, so a slow server can't hold every waiter.
LOAD_TIMEOUT_S = 120.0
MAX_CACHE_ENTRIES = 10_000


class SingleFlightCache(Generic[V]):
    """A bounded LRU cache with per-entry expiry; concurrent misses share a load.

    Failed loads are not cached: every waiter sees the error and the next call
    loads again.
    """

    def __init__(self) -> None:
        """An empty cache."""
        self._entries: OrderedDict[str, tuple[float, V]] = OrderedDict()
        self._inflight: dict[str, asyncio.Task[V]] = {}

    async def get(
        self,
        key: str,
        load: Callable[[], Awaitable[tuple[V, float]]],
        *,
        flight: str | None = None,
    ) -> V:
        """The value under `key`, loaded once by whichever caller asks first.

        Args:
            key: The cache key.
            load: Loads the value and says how many seconds it stays valid.
            flight: Which concurrent misses share a load, `key` by default.
                A value loaded in any flight is kept under `key`; a failure
                reaches only the calls of its own flight.

        Returns:
            The cached or loaded value.
        """
        entry = self._entries.get(key)
        if entry is not None:
            expires_at, value = entry
            if expires_at > time.monotonic():
                self._entries.move_to_end(key)
                return value
            del self._entries[key]
        shared = key if flight is None else flight
        task = self._inflight.get(shared)
        if task is None:
            # Its own task, so cancelling the caller that started a load does
            # not cancel it for the other callers waiting on it.
            task = asyncio.create_task(self._load(key, shared, load))
            task.add_done_callback(_retrieve_exception)
            self._inflight[shared] = task
        return await asyncio.shield(task)

    async def _load(
        self,
        key: str,
        shared: str,
        load: Callable[[], Awaitable[tuple[V, float]]],
    ) -> V:
        try:
            value, ttl = await asyncio.wait_for(load(), LOAD_TIMEOUT_S)
        except asyncio.TimeoutError:
            raise ZenMLUnavailable(
                f"ZenML did not answer within {LOAD_TIMEOUT_S:.0f} s. Try again."
            ) from None
        finally:
            self._inflight.pop(shared, None)
        if ttl > 0:
            self._entries[key] = (time.monotonic() + ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > MAX_CACHE_ENTRIES:
                self._entries.popitem(last=False)
        return value


def _retrieve_exception(task: asyncio.Task[object]) -> None:
    """Mark a failed load's error as seen when no caller is left to await it.

    Args:
        task: The finished load.
    """
    if not task.cancelled():
        task.exception()
