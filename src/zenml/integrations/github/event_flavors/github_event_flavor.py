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
"""Example file of what an event Plugin could look like."""
from typing import Type

from fastapi import APIRouter

from zenml.events.base_event_flavor import (
    BaseEventFlavor,
    EventFilterConfig,
    EventSourceConfig,
)
from zenml.integrations.github import GITHUB_EVENT_FLAVOR
from zenml.integrations.github.event_handlers.github_event_handler import (
    GithubEvent,
    GithubEventFilterConfiguration,
    GithubEventHandler,
    GithubEventSourceConfiguration,
)


class GithubEventSourceFlavor(BaseEventFlavor):
    """Enables users to configure github event sources."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GITHUB_EVENT_FLAVOR

    @property
    def event_handler_class(self) -> Type[GithubEventHandler]:
        """Returns the flavor specific `BaseEventHandler` class.

        Returns:
            The event handler class.
        """
        return GithubEventHandler

    @property
    def event_source_config_class(self) -> Type[EventSourceConfig]:
        """Config class for the event source.

        Returns:
            The config class.
        """
        return GithubEventSourceConfiguration

    @property
    def event_filter_config_class(self) -> Type[EventFilterConfig]:
        """Config class for the event source.

        Returns:
            The config class.
        """
        return GithubEventFilterConfiguration

    @staticmethod
    def register_endpoint(router: APIRouter):
        """Register the github webhook to receive events from github."""

        @router.post("/github-webhook")
        async def post_event(event: GithubEvent):
            from zenml.zen_server.utils import zen_store

            GithubEventHandler(
                flavor=GITHUB_EVENT_FLAVOR, zen_store=zen_store()
            ).process_event(event)
