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
"""Event dispatcher base functionality."""

import atexit
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from zenml.dispatcher.handler import EventHandler
from zenml.zen_stores.schemas import PipelineRunSchema

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Event Dispatcher class."""

    _instance: "EventDispatcher | None " = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        """Event Dispatcher constructor."""
        self._event_handlers: list[EventHandler] = []
        self._handlers_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=8,
            thread_name_prefix="event-dispatcher",
        )
        atexit.register(self.shutdown)

    def register_event_handler(self, event_handler: EventHandler) -> None:
        """Register an event handler.

        Args:
            event_handler: An event handler to register.
        """
        with self._handlers_lock:
            self._event_handlers.append(event_handler)

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Future[Any]:
        """Submit work to be executed asynchronously.

        Args:
            func: Callable to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            A Future representing the execution.
        """
        future = self._executor.submit(
            self._safe_invoke, func, *args, **kwargs
        )
        future.add_done_callback(self._log_future_exception)
        return future

    def _safe_invoke(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Safely invoke a callable."""
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception(
                "Asynchronous dispatcher task failed: %s",
                getattr(func, "__qualname__", repr(func)),
            )
            raise

    @staticmethod
    def _log_future_exception(future: Future[Any]) -> None:
        """Log unexpected future failures."""
        exc = future.exception()
        if exc is not None:
            logger.exception(
                "Unexpected event dispatcher future failure.", exc_info=exc
            )

    def handle_run_status_update(
        self,
        run: PipelineRunSchema,
    ) -> None:
        """Handle a status update on a PipelineRun object.

        Note: Status updates are a run-specific concept. This
        method is non-generalisable across types by design. To support richer events
        like `creation` or `deletion` of a resource we should extend the interface
        signature with generic methods.

        Args:
            run: A PipelineRunSchema object (with a status change).
        """
        with self._handlers_lock:
            handlers = list(self._event_handlers)

        if not handlers:
            return

        for event_handler in handlers:
            logger.debug(
                "Event handler: %s picking up %s status change to %s",
                event_handler.__class__.__name__,
                run.id,
                run.status,
            )
            self.submit(
                event_handler.handle_run_status_update,
                run=run,
            )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the dispatcher.

        Args:
            wait: Flag indicating whether to wait for shutdown.
        """
        try:
            self._executor.shutdown(wait=wait)
        except Exception as exc:
            logger.exception("Failed to shutdown executor", exc_info=exc)

    @staticmethod
    def get_event_dispatcher() -> "EventDispatcher":
        """Getter utility - returns a fresh or cached EventDispatcher.

        Returns:
            An EventDispatcher instance.
        """
        if not EventDispatcher._instance:
            with EventDispatcher._instance_lock:
                if not EventDispatcher._instance:
                    EventDispatcher._instance = EventDispatcher()

        return EventDispatcher._instance
