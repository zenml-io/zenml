# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Process-local admission control for execution-retention payload work."""

from contextlib import contextmanager
from threading import BoundedSemaphore, Lock
from typing import Hashable, Iterator, Optional, Set

from zenml.exceptions import ExecutionRetentionBusyError

MAX_CONCURRENT_RETENTION_OPERATIONS = 4


class RetentionCapacity:
    """Bound aggregate retention work and duplicate keyed operations."""

    def __init__(self, max_operations: int) -> None:
        """Create a fixed process-local capacity budget.

        Args:
            max_operations: Maximum admitted payload operations.

        Raises:
            ValueError: If the capacity is not positive.
        """
        if max_operations < 1:
            raise ValueError("Retention capacity must be positive.")
        self.max_operations = max_operations
        self._semaphore = BoundedSemaphore(max_operations)
        self._keys: Set[Hashable] = set()
        self._lock = Lock()

    @contextmanager
    def claim(self, key: Optional[Hashable] = None) -> Iterator[None]:
        """Claim capacity without queuing more payload work.

        Args:
            key: Optional operation identity that may only run once at a time.

        Yields:
            Control while the claim is held.

        Raises:
            ExecutionRetentionBusyError: If the process budget or key is busy.
        """
        with self._lock:
            if key is not None and key in self._keys:
                raise ExecutionRetentionBusyError(
                    "This execution-retention operation is already running."
                )
            if not self._semaphore.acquire(blocking=False):
                raise ExecutionRetentionBusyError(
                    "This server replica is at its execution-retention "
                    "capacity. Retry the operation later."
                )
            if key is not None:
                self._keys.add(key)
        try:
            yield
        finally:
            with self._lock:
                if key is not None:
                    self._keys.remove(key)
                self._semaphore.release()
