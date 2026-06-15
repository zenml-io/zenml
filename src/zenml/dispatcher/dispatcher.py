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
"""Event dispatcher that fans out run lifecycle events to handlers."""

import threading
from typing import List

from zenml.dispatcher.handler import EventHandler
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse
from zenml.utils.singleton import SingletonMetaClass

logger = get_logger(__name__)


class EventDispatcher(metaclass=SingletonMetaClass):
    """Process-wide broadcaster of pipeline run lifecycle events."""

    def __init__(self) -> None:
        """Initialize the dispatcher with an empty handler list."""
        self._event_handlers: List[EventHandler] = []
        self._handlers_lock = threading.Lock()

    def register_event_handler(self, event_handler: EventHandler) -> None:
        """Register an event handler.

        Args:
            event_handler: An event handler to register.
        """
        with self._handlers_lock:
            self._event_handlers.append(event_handler)

    def unregister_event_handler(self, event_handler: EventHandler) -> None:
        """Unregister a previously-registered event handler.

        No-op if the handler isn't registered.

        Args:
            event_handler: The event handler instance to remove.
        """
        with self._handlers_lock:
            try:
                self._event_handlers.remove(event_handler)
            except ValueError:
                pass

    def has_handlers(self) -> bool:
        """Return True if any handlers are registered.

        Returns:
            Whether the dispatcher would fan out to at least one handler.
        """
        with self._handlers_lock:
            return bool(self._event_handlers)

    def handle_run_status_update(
        self,
        run: PipelineRunResponse,
    ) -> None:
        """Handle a status update on a pipeline run.

        Args:
            run: The pipeline run whose status has changed.
        """
        with self._handlers_lock:
            handlers = list(self._event_handlers)

        for event_handler in handlers:
            try:
                logger.debug(
                    "Event handler: %s picking up %s status change to %s",
                    event_handler.__class__.__name__,
                    run.id,
                    run.status,
                )
                event_handler.handle_run_status_update(run)
            except Exception as exc:
                logger.exception(
                    "%s failed to handle update",
                    event_handler.__class__.__name__,
                    exc_info=exc,
                )
