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
"""Base classes for event handlers registered with the dispatcher."""

from abc import ABC, abstractmethod

from zenml.models import PipelineRunResponse


class EventHandler(ABC):
    """Abstract base for handlers registered with `EventDispatcher`."""

    @abstractmethod
    def handle_run_status_update(
        self,
        run: PipelineRunResponse,
    ) -> None:
        """Handle a status update on a pipeline run.

        Args:
            run: The pipeline run whose status has changed.
        """

    @classmethod
    async def create(cls) -> "EventHandler":
        """Factory used by the source loader.

        Needs to be implemented if a handler is specified via
        `server_config.event_handler_sources`.

        Raises:
            NotImplementedError: Always.

        Returns:
            Handler instance.
        """
        raise NotImplementedError(
            f"{cls.__name__}.create() is not implemented."
        )
