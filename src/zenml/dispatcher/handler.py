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
"""Event Handler base functionality."""

from abc import ABC, abstractmethod

from zenml.models import PipelineRunResponse


class EventHandler(ABC):
    """Abstraction for EventHandler classes."""

    @abstractmethod
    def handle_run_status_update(
        self,
        run: PipelineRunResponse,
    ) -> None:
        """Handle a status update on a PipelineRun object.

        Note: Status updates are a run-specific concept. This
        method is non-generalizable across types by design. To support richer events
        like `creation` or `deletion` of a resource we should extend the interface
        signature with generic methods.

        Args:
            run: A PipelineRunResponse object (with a status change).
        """
        pass

    @classmethod
    async def create(cls) -> "EventHandler":
        """Factory for source-loaded handlers.

        Override to support being loaded via
        `server_config.event_handler_sources`. Handlers constructed
        directly with explicit dependencies (e.g., the streaming
        end-event handler) don't need to override this.

        Returns:
            An EventHandler instance.

        Raises:
            NotImplementedError: If the subclass isn't source-loadable.
        """
        raise NotImplementedError(
            f"{cls.__name__} cannot be source-loaded; instantiate it "
            "directly with the required dependencies."
        )
