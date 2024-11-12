#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Memory cache module for the ZenML server."""

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.utils.singleton import SingletonMetaClass

logger = get_logger(__name__)


class MemoryCacheEntry:
    """Simple class to hold cache entry data."""

    def __init__(self, value: Any, expiry: int) -> None:
        """Initialize a cache entry with value and expiry time.

        Args:
            value: The value to store in the cache.
            expiry: The expiry time in seconds.
        """
        self.value: Any = value
        self.expiry: int = expiry
        self.timestamp: float = time.time()

    @property
    def expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp >= self.expiry


class MemoryCache(metaclass=SingletonMetaClass):
    """Simple in-memory cache with expiry and capacity management.

    This cache is thread-safe and can be used in both synchronous and
    asynchronous contexts. It uses a simple LRU (Least Recently Used) eviction
    strategy to manage the cache size.

    Each cache entry has a key, value, timestamp, and expiry. The cache
    automatically removes expired entries and evicts the oldest entry when
    the cache reaches its maximum capacity.


    Usage Example:

        cache = MemoryCache()
        uuid_key = UUID("12345678123456781234567812345678")

        cached_or_real_object = cache.get_or_cache(
            uuid_key, lambda: "sync_data", expiry=120
        )
        print(cached_or_real_object)
    """

    def __init__(self, max_capacity: int, default_expiry: int) -> None:
        """Initialize the cache with a maximum capacity and default expiry time.

        Args:
            max_capacity: The maximum number of entries the cache can hold.
            default_expiry: The default expiry time in seconds.
        """
        self.cache: Dict[UUID, MemoryCacheEntry] = OrderedDict()
        self.max_capacity = max_capacity
        self.default_expiry = default_expiry
        self._lock = Lock()

    def set(self, key: UUID, value: Any, expiry: Optional[int] = None) -> None:
        """Insert value into cache with optional custom expiry time in seconds.

        Args:
            key: The key to insert the value with.
            value: The value to insert into the cache.
            expiry: The expiry time in seconds. If None, uses the default expiry.
        """
        with self._lock:
            self.cache[key] = MemoryCacheEntry(
                value=value, expiry=expiry or self.default_expiry
            )
            self._cleanup()

    def get(self, key: UUID) -> Optional[Any]:
        """Retrieve value if it's still valid; otherwise, return None.

        Args:
            key: The key to retrieve the value for.

        Returns:
            The value if it's still valid; otherwise, None.
        """
        with self._lock:
            return self._get_internal(key)

    def _get_internal(self, key: UUID) -> Optional[Any]:
        """Helper to retrieve a value without lock (internal use only).

        Args:
            key: The key to retrieve the value for.

        Returns:
            The value if it's still valid; otherwise, None.
        """
        entry = self.cache.get(key)
        if entry and not entry.expired:
            return entry.value
        elif entry:
            del self.cache[key]  # Invalidate expired entry
        return None

    def _cleanup(self) -> None:
        """Remove expired or excess entries."""
        # Remove expired entries
        keys_to_remove = [k for k, v in self.cache.items() if v.expired]
        for k in keys_to_remove:
            del self.cache[k]

        # Ensure we don't exceed max capacity
        while len(self.cache) > self.max_capacity:
            self.cache.popitem(last=False)  # type: ignore[call-arg]


F = Callable[[UUID], Optional[Any]]


def cache_result(
    expiry: Optional[int] = None,
) -> Callable[[F], F]:
    """A decorator to cache the result of a function based on a UUID key argument.

    Args:
        expiry: Custom time in seconds for the cache entry to expire. If None,
            uses the default expiry time.

    Returns:
        A decorator that wraps a function, caching its results based on a UUID
        key.
    """

    def decorator(func: F) -> F:
        """The actual decorator that wraps the function with caching logic.

        Args:
            func: The function to wrap.

        Returns:
            The wrapped function with caching logic.
        """

        def wrapper(key: UUID) -> Optional[Any]:
            """The wrapped function with caching logic.

            Args:
                key: The key to use for caching.
                *args: Additional positional arguments.
                **kwargs: Additional keyword arguments.

            Returns:
                The result of the original function, either from cache or
                freshly computed.
            """
            from zenml.zen_server.utils import memcache

            cache = memcache()

            # Attempt to retrieve the result from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(
                    f"Memory cache hit for key: {key} and func: {func.__name__}"
                )
                return cached_value

            # Call the original function and cache its result
            result = func(key)
            cache.set(key, result, expiry)
            return result

        return wrapper

    return decorator
