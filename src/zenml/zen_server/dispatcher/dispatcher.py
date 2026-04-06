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

import logging

from zenml.zen_server.dispatcher.handler import EventHandler
from zenml.zen_stores.schemas import PipelineRunSchema

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Event Dispatcher class."""

    def __init__(self, event_handlers: list[EventHandler]):
        """Event Dispatcher constructor.

        Args:
            event_handlers: A list of registered event handlers.
        """
        self._event_handlers = event_handlers

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
        for event_handler in self._event_handlers:
            logger.debug(
                "Event handler: %s picking up %s status change to %s",
                event_handler.__class__.__name__,
                run.id,
                run.status,
            )
            # TODO: Offload to thread.
            event_handler.handle_run_status_update(
                run=run,
            )
