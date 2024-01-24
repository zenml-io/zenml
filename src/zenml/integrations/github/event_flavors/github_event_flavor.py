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
from typing import List, Type
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from zenml.events.base_event import Event
from zenml.events.base_event_flavor import (
    BaseEventFlavor,
    EventFilterConfig,
    EventSourceConfig,
)
from zenml.integrations.github import GITHUB_EVENT_FLAVOR

# -------------------- Github Event Models -----------------------------------


class Commit(BaseModel):
    """Github Event."""

    id: str
    message: str
    url: str


class Repository(BaseModel):
    """Github Repository."""

    id: int
    name: str
    full_name: str


class PushEvent(Event):
    """Push Event from Github."""

    ref: str
    before: str
    after: str
    repository: Repository
    commits: List[Commit]


# -------------------- Configuration Models ----------------------------------


class GithubEventSourceConfiguration(EventSourceConfig):
    """Configuration for github source filters."""

    repo: str


class GithubEventFilterConfiguration(EventFilterConfig):
    """Configuration for github event filters."""

    branch: str


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
        async def post_event(body: PushEvent):
            print(body)
            # TODO: Process body
            #  Filter triggers to find matching filter
            #  Forward "Event/Trigger/.." Object to the Event Hub
