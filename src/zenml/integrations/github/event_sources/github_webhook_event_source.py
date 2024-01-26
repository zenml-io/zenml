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
"""Implementation of the github event handler."""
from functools import partial
from typing import List, Optional, Type
from uuid import UUID

from pydantic import BaseModel

from zenml.event_sources.base_event_source_plugin import BaseEvent
from zenml.event_sources.webhooks.base_webhook_event_plugin import (
    BaseWebhookEventSourcePlugin,
    WebhookEventFilterConfig,
    WebhookEventSourceConfig,
)
from zenml.models import (
    EventSourceFilter,
    EventSourceResponse,
    TriggerFilter,
    TriggerResponse,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.pagination_utils import depaginate

# -------------------- Utils -----------------------------------


class GithubEventType(StrEnum):
    """Collection of all possible Github Events."""

    PUSH_EVENT = "push_event"
    TAG_EVENT = "tag_event"
    PR_EVENT = "pull_request_event"


# -------------------- Github Event Models -----------------------------------


class Commit(BaseModel):
    """Github Event."""

    id: str
    message: str
    url: str
    author: str


class Tag(BaseModel):
    """Github Tag."""

    id: str
    name: str
    commit: Commit


class User(BaseModel):
    """Github User."""

    id: int
    username: str
    email: str


class PullRequest(BaseModel):
    """Github Pull Request."""

    id: str
    number: int
    title: str
    author: User
    merged: bool
    merge_commit: Commit


class Repository(BaseModel):
    """Github Repository."""

    id: int
    name: str
    full_name: str
    owner: User


class GithubEvent(BaseEvent):
    """Push Event from Github."""

    ref: str
    before: str
    after: str
    repository: Repository
    commits: List[Commit]
    tags: List[Tag]
    pull_requests: List[PullRequest]

    @property
    def branch(self) -> Optional[str]:
        """THe branch the event happened on."""
        if self.ref.startswith("refs/heads/"):
            return self.ref.split("/")[-1]
        return None

    @property
    def event_type(self) -> str:
        """The type of github event."""
        if self.ref.startswith("refs/heads/"):
            return GithubEventType.PUSH_EVENT
        elif self.ref.startswith("refs/tags/"):
            return GithubEventType.TAG_EVENT
        elif len(self.pull_requests) > 0:
            return GithubEventType.PR_EVENT
        else:
            return "unknown"


# -------------------- Configuration Models ----------------------------------


class GithubWebhookEventFilterConfiguration(WebhookEventFilterConfig):
    """Configuration for github event filters."""

    branch: Optional[str]
    event_type: Optional[GithubEventType]

    def event_matches_filter(self, event: GithubEvent) -> bool:
        """Checks the filter against the inbound event."""
        if self.event_type and event.event_type != self.event_type:
            # Mismatch for the action
            return False
        if self.branch and event.branch != self.branch:
            # Mismatch for the branch
            return False
        return True


class GithubWebhookEventSourceConfiguration(WebhookEventSourceConfig):
    """Configuration for github source filters."""

    repo: str


# -------------------- Github Webhook Plugin -----------------------------------


class GithubWebhookEventSourcePlugin(BaseWebhookEventSourcePlugin):
    """Handler for all github events."""

    @property
    def config_class(self) -> Type[GithubWebhookEventSourceConfiguration]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return GithubWebhookEventSourceConfiguration

    def _get_all_relevant_event_sources(
        self, event: GithubEvent
    ) -> List[UUID]:
        """Filter Event Sources for flavor and flavor specific properties.

        For github event sources this will compare the configured repository
        of the inbound event to all github event sources.

        Args:
            event: The inbound Event.

        Returns: A list of all matching Event Source IDs.
        """
        # get all event sources configured for this flavor
        event_sources: List[EventSourceResponse] = depaginate(
            partial(
                self.zen_store.list_event_sources,
                event_source_filter_model=EventSourceFilter(flavor="github"),
                hydrate=True,
            )
        )  # TODO: investigate how this can be improved

        ids_list: List[UUID] = []

        # TODO: improve this
        if isinstance(event, dict):
            event = GithubEvent(**event)

        for es in event_sources:
            esc = GithubWebhookEventSourceConfiguration(
                **es.metadata.configuration
            )
            if esc.repo == event.repository.name:
                ids_list.append(es.id)

        return ids_list

    def _get_matching_triggers(
        self, event_source_ids: List[UUID], event: GithubEvent
    ) -> List[UUID]:
        """Get all Triggers with matching event filters.

        For github events this will compare the configured event filters
        of all matching triggers with the inbound event.

        Args:
            event_source_ids: All matching event source ids.
            event: The inbound Event.

        Returns: A list of all matching Event Source IDs.
        """
        # get all event sources configured for this flavor
        triggers: List[TriggerResponse] = depaginate(
            partial(
                self.zen_store.list_triggers,
                trigger_filter_model=TriggerFilter(
                    event_source_id=event_source_ids[
                        0
                    ]  # TODO: Handle for multiple source_ids
                ),
                hydrate=True,
            )
        )

        # TODO: improve this
        if isinstance(event, dict):
            event = GithubEvent(**event)

        ids_list: List[UUID] = []

        for trigger in triggers:
            event_filter = GithubWebhookEventFilterConfiguration(
                **trigger.metadata.event_filter
            )
            if event_filter.event_matches_filter(event=event):
                ids_list.append(trigger.id)

        return ids_list
