#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Context variable utilities."""

import threading
from contextvars import ContextVar
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class ContextVarList(Generic[T]):
    """Thread-safe wrapper around ContextVar[List] with atomic add/remove operations."""

    def __init__(self, name: str) -> None:
        """Initialize the context variable list.

        Args:
            name: The name for the underlying ContextVar.
        """
        # Use None as default to avoid mutable default issues
        self._context_var: ContextVar[Optional[List[T]]] = ContextVar(
            name, default=None
        )
        # Lock to ensure atomic operations
        self._lock = threading.Lock()

    def get(self) -> List[T]:
        """Get the current list value. Returns empty list if not set.

        Returns:
            The current list value.
        """
        value = self._context_var.get()
        return value if value is not None else []

    def add(self, item: T) -> None:
        """Thread-safely add an item to the list.

        Args:
            item: The item to add to the list.
        """
        with self._lock:
            current_list = self.get()
            if not any(x is item for x in current_list):
                new_list = current_list + [item]
                self._context_var.set(new_list)

    def remove(self, item: T) -> None:
        """Thread-safely remove an item from the list.

        Args:
            item: The item to remove from the list.
        """
        with self._lock:
            current_list = self.get()
            if any(x is item for x in current_list):
                new_list = [x for x in current_list if x is not item]
                self._context_var.set(new_list)
