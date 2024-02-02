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
"""Implementation of the github webhook event source."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from pydantic import BaseModel, Extra

from zenml.event_sources.base_event_source import BaseEvent
from zenml.event_sources.webhooks.base_webhook_event import (
    BaseWebhookEventSource,
    WebhookEventFilterConfig,
    WebhookEventSourceConfig,
)
from zenml.logger import get_logger
from zenml.models import (
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    SecretRequest,
    SecretUpdate,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import SecretField
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)

# -------------------- Utils -----------------------------------


class GithubEventType(StrEnum):
    """Collection of all possible Github Events."""

    PUSH_EVENT = "push_event"
    TAG_EVENT = "tag_event"
    PR_EVENT = "pull_request_event"


# -------------------- Github Event Models -----------------------------------


class User(BaseModel):
    """Github User."""

    name: str
    email: str
    username: str


class Commit(BaseModel):
    """Github Event."""

    id: str
    message: str
    url: str
    author: User


class Tag(BaseModel):
    """Github Tag."""

    id: str
    name: str
    commit: Commit


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
    html_url: str


class GithubEvent(BaseEvent):
    """Push Event from Github."""

    ref: str
    before: str
    after: str
    repository: Repository
    commits: List[Commit]
    head_commit: Optional[Commit]
    tags: Optional[List[Tag]]
    pull_requests: Optional[List[PullRequest]]

    class Config:
        """Pydantic configuration class."""

        extra = Extra.allow

    @property
    def branch(self) -> Optional[str]:
        """THe branch the event happened on."""
        if self.ref.startswith("refs/heads/"):
            return "/".join(self.ref.split("/")[2:])
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

    repo: Optional[str]
    branch: Optional[str]
    event_type: Optional[GithubEventType]

    def event_matches_filter(self, event: BaseEvent) -> bool:
        """Checks the filter against the inbound event."""
        if not isinstance(event, GithubEvent):
            return False
        if self.event_type and event.event_type != self.event_type:
            # Mismatch for the action
            return False
        if self.repo and event.repository.full_name != self.repo:
            # Mismatch for the repository
            return False
        if self.branch and event.branch != self.branch:
            # Mismatch for the branch
            return False
        return True


class GithubWebhookEventSourceConfiguration(WebhookEventSourceConfig):
    """Configuration for github source filters."""

    webhook_secret: Optional[str] = SecretField()
    webhook_secret_id: Optional[UUID]


# -------------------- Github Webhook Plugin -----------------------------------


class GithubWebhookEventSource(BaseWebhookEventSource):
    """Handler for all github events."""

    @property
    def config_class(self) -> Type[GithubWebhookEventSourceConfiguration]:
        """Returns the webhook event source configuration class.

        Returns:
            The configuration.
        """
        return GithubWebhookEventSourceConfiguration

    @property
    def filter_class(self) -> Type[GithubWebhookEventFilterConfiguration]:
        """Returns the webhook event filter configuration class.

        Returns:
            The event filter configuration class.
        """
        return GithubWebhookEventFilterConfiguration

    def _interpret_event(self, event: Dict[str, Any]) -> GithubEvent:
        """Converts the generic event body into a event-source specific pydantic model.

        Args:
            event: The generic event body

        Return:
            An instance of the event source specific pydantic model.

        Raises:
            ValueError: If the event body can not be parsed into the pydantic model.
        """
        try:
            event = GithubEvent(**event)
        except ValueError as e:
            logger.exception(e)
            # TODO: Remove this - currently useful for debugging
            with open(
                f'{datetime.now().strftime("%Y%m%d%H%M%S")}.json', "w"
            ) as f:
                json.dump(event, f)
            raise ValueError("Event did not match the pydantic model.")
        else:
            return event

    def _update_event_source(
            self,
            event_source_id: UUID,
            event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Wraps the zen_store update method to add plugin specific functionality.

        Args:
            event_source_id: The ID of the event_source to update.
            event_source_update: The update to be applied to the event_source.

        Returns:
            The event source response body.
        """
        original_event_source = self.zen_store.get_event_source(
            event_source_id=event_source_id
        )

        updated_event_source = self.zen_store.update_event_source(
            event_source_id=event_source_id,
            event_source_update=event_source_update,
        )

        if event_source_update.rotate_secret:
            # In case the secret is being rotated
            secret_key_value = random_str(12)
            webhook_secret = SecretUpdate(
                values={"webhook_secret": secret_key_value}
            )
            self.zen_store.update_secret(
                secret_id=original_event_source.metadata.configuration[
                    "webhook_secret_id"
                ],
                secret_update=webhook_secret,
            )
            updated_event_source.metadata.configuration[
                "webhook_secret"
            ] = secret_key_value
        return updated_event_source

    def _create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method for plugin specific functionality.

        Args:
            event_source: Request model for the event source.

        Returns:
            The created event source.
        """
        try:
            config = GithubWebhookEventSourceConfiguration(
                **event_source.configuration
            )
        except ValueError:
            raise ValueError("Event Source configuration invalid.")

        secret_key_value = random_str(12)
        webhook_secret = SecretRequest(
            name=f"event_source-{event_source.name}-{random_str(4)}".lower(),
            values={"webhook_secret": secret_key_value},
            workspace=event_source.workspace,
            user=event_source.user,
        )
        secret = self.zen_store.create_secret(webhook_secret)

        config.webhook_secret_id = secret.id
        event_source.configuration = config.dict()

        created_event_source = self.zen_store.create_event_source(
            event_source=event_source
        )
        created_event_source.metadata.configuration[
            "webhook_secret"
        ] = secret_key_value
        return created_event_source

    def _get_event_source(self, event_source_id: UUID) -> EventSourceResponse:
        """Wraps the zen_store getter method to add plugin specific functionality."""
        created_event_source = self.zen_store.get_event_source(
            event_source_id=event_source_id
        )
        webhook_secret_id = created_event_source.metadata.configuration[
            "webhook_secret_id"
        ]

        secret_value = self.zen_store.get_secret(
            secret_id=webhook_secret_id
        ).body["webhook_secret"]
        created_event_source.metadata.configuration[
            "webhook_secret"
        ] = secret_value
        return created_event_source
