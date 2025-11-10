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

import contextvars
import threading
from contextvars import ContextVar
from typing import Any, ClassVar, Generic, List, Optional, TypeVar

from typing_extensions import Self

T = TypeVar("T")


class BaseContext:
    """Base context class."""

    __context_var__: ClassVar[contextvars.ContextVar[Self]]

    def __init__(self) -> None:
        """Initialize the context."""
        self._token: Optional[contextvars.Token[Any]] = None

    @classmethod
    def get(cls: type[Self]) -> Optional[Self]:
        """Get the active context.

        Returns:
            The active context.
        """
        return cls.__context_var__.get(None)

    @classmethod
    def is_active(cls: type[Self]) -> bool:
        """Check if the context is active.

        Returns:
            True if the context is active, False otherwise.
        """
        return cls.get() is not None

    def __enter__(self) -> Self:
        """Enter the context.

        Returns:
            The context object.
        """
        self._token = self.__context_var__.set(self)
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit the context.

        Args:
            *_: Unused keyword arguments.

        Raises:
            RuntimeError: If the context has not been entered.
        """
        if not self._token:
            raise RuntimeError(
                f"Can't exit {self.__class__.__name__} because it has not been "
                "entered."
            )
        self.__context_var__.reset(self._token)


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
