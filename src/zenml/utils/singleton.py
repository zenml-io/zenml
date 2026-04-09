#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utility class to turn classes into singleton classes."""

import contextvars
from typing import Any, Optional, TypeVar, cast

SingletonInstance = TypeVar("SingletonInstance")


class SingletonMetaClass(type):
    """Singleton metaclass.

    Use this metaclass to make any class into a singleton class:

    ```python
    class OneRing(metaclass=SingletonMetaClass):
        def __init__(self, owner):
            self._owner = owner

        @property
        def owner(self):
            return self._owner

    the_one_ring = OneRing('Sauron')
    the_lost_ring = OneRing('Frodo')
    print(the_lost_ring.owner)  # Sauron
    OneRing._clear() # ring destroyed
    ```
    """

    _singleton_instance: object | None = None

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize a singleton class.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)
        cls._singleton_instance = None

    def __call__(
        cls: type[SingletonInstance], *args: Any, **kwargs: Any
    ) -> SingletonInstance:
        """Create or return the singleton instance.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The singleton instance.
        """
        meta_cls = cast("SingletonMetaClass", cls)
        if meta_cls._singleton_instance is None:
            meta_cls._singleton_instance = cast(
                object, type.__call__(cls, *args, **kwargs)
            )

        return cast(SingletonInstance, meta_cls._singleton_instance)

    def _clear(
        cls: type[SingletonInstance],
        instance: Optional[SingletonInstance] = None,
    ) -> None:
        """Clear or replace the singleton instance.

        Args:
            instance: The new singleton instance.
        """
        cast("SingletonMetaClass", cls)._singleton_instance = instance

    def _instance(
        cls: type[SingletonInstance],
    ) -> Optional[SingletonInstance]:
        """Get the singleton instance.

        Returns:
            The singleton instance.
        """
        return cast(
            Optional[SingletonInstance],
            cast("SingletonMetaClass", cls)._singleton_instance,
        )

    def _exists(cls) -> bool:
        """Check if the singleton instance exists.

        Returns:
            `True` if the singleton instance exists, `False` otherwise.
        """
        return cls._singleton_instance is not None


class ThreadLocalSingleton(type):
    """Thread-local singleton metaclass using contextvars.

    This metaclass creates singleton instances that are isolated per execution
    context (thread or asyncio task). Each context gets its own singleton
    instance, allowing for thread-safe and coroutine-safe singleton behavior.

    Use this metaclass when you need singleton behavior but want isolation
    between different execution contexts:

    ```python
    class DatabaseConnection(metaclass=ContextVarSingleton):
        def __init__(self, connection_string: str):
            self._connection_string = connection_string
            self._connected = False

        def connect(self):
            if not self._connected:
                # Connect to database
                self._connected = True

        @property
        def connection_string(self):
            return self._connection_string

    # In context 1 (e.g., thread 1)
    db1 = DatabaseConnection("postgres://localhost/db1")
    db1.connect()

    # In context 2 (e.g., thread 2)
    db2 = DatabaseConnection("postgres://localhost/db2")
    # db2 is a different instance from db1, isolated by context
        ```
    """

    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        """Initialize a thread-local singleton class.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)
        cls.__context_instance: contextvars.ContextVar[
            Optional["ThreadLocalSingleton"]
        ] = contextvars.ContextVar(f"{cls.__name__}_instance", default=None)

    def __call__(cls, *args: Any, **kwargs: Any) -> "ThreadLocalSingleton":
        """Create or return the singleton instance for the current context.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The singleton instance for the current execution context.
        """
        instance = cls.__context_instance.get()
        if instance is None:
            instance = cast(
                "ThreadLocalSingleton", super().__call__(*args, **kwargs)
            )
            cls.__context_instance.set(instance)

        return instance

    def _clear(cls, instance: Optional["ThreadLocalSingleton"] = None) -> None:
        """Clear or replace the singleton instance in the current context.

        Args:
            instance: The new singleton instance for the current context.
                If None, clears the current instance.
        """
        cls.__context_instance.set(instance)

    def _instance(cls) -> Optional["ThreadLocalSingleton"]:
        """Get the singleton instance for the current context.

        Returns:
            The singleton instance for the current execution context,
            or None if no instance exists in this context.
        """
        return cls.__context_instance.get()

    def _exists(cls) -> bool:
        """Check if a singleton instance exists in the current context.

        Returns:
            True if a singleton instance exists in the current context,
            False otherwise.
        """
        return cls.__context_instance.get() is not None
