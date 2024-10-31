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
"""Callback registry implementation."""

from typing import Any, Callable, Dict, List, Tuple

from typing_extensions import ParamSpec

from zenml.logger import get_logger

P = ParamSpec("P")

logger = get_logger(__name__)


class CallbackRegistry:
    """Callback registry class."""

    def __init__(self) -> None:
        """Initializes the callback registry."""
        self._callbacks: List[
            Tuple[Callable[P, Any]], Tuple[Any], Dict[str, Any]
        ] = []

    def register_callback(
        self, callback: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Register a callback.

        Args:
            callback: The callback to register.
            *args: Arguments to call the callback with.
            **kwargs: Keyword arguments to call the callback with.
        """
        self._callbacks.append((callback, args, kwargs))

    def reset(self) -> None:
        """Reset the callbacks."""
        self._callbacks = []

    def execute_callbacks(self, raise_on_exception: bool) -> None:
        """Execute all registered callbacks.

        Args:
            raise_on_exception: If True, exceptions raised during the execution
                of the callbacks will be raised. If False, a warning with the
                exception will be logged instead.

        Raises:
            Exception: Exceptions raised in any of the callbacks if
                `raise_on_exception` is set to True.
        """
        for callback, args, kwargs in self._callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                if raise_on_exception:
                    raise e
                else:
                    logger.warning("Failed to run callback: %s", str(e))
