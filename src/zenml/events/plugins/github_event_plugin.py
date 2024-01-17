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
from typing import ClassVar, List
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from zenml.enums import EventConfigurationType
from zenml.events.base_event_flavor import BaseEventFlavor, EventConfig

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


class PushEvent(BaseModel):
    """Push Event from Github."""

    ref: str
    before: str
    after: str
    repository: Repository
    commits: List[Commit]


# -------------------- Configuration Models ----------------------------------


class GithubEventSourceConfiguration(EventConfig):
    """Configuration for github source filters."""

    repo: str


class GithubEventSourceFlavor(BaseEventFlavor):
    """Enables users to configure github event sources."""

    EVENT_FLAVOR: ClassVar[str] = "GITHUB"
    CONFIGURATION_TYPE: ClassVar[
        EventConfigurationType
    ] = EventConfigurationType.SOURCE

    config: GithubEventSourceConfiguration

    @staticmethod
    def register_endpoint(router: APIRouter):
        """Register the github webhook to receive events from github."""

        @router.post("/github-webhook")
        async def post_event(body: PushEvent):
            print(body)


class GithubEventFilterConfiguration(EventConfig):
    """Configuration for github event filters."""

    source_id: UUID
    branch: str


class GithubEventFilterFlavor(BaseEventFlavor):
    """Allows users to configure filters on events coming from a github source."""

    EVENT_FLAVOR: ClassVar[str] = "GITHUB"
    CONFIGURATION_TYPE: ClassVar[
        EventConfigurationType
    ] = EventConfigurationType.FILTER

    config: GithubEventFilterConfiguration
