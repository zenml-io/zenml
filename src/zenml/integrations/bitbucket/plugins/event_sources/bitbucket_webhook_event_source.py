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
"""Implementation of the Bitbucket webhook event source."""

from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zenml.enums import SecretScope
from zenml.event_sources.base_event import (
    BaseEvent,
)
from zenml.event_sources.base_event_source import EventSourceConfig
from zenml.event_sources.webhooks.base_webhook_event_source import (
    BaseWebhookEventSourceFlavor,
    BaseWebhookEventSourceHandler,
    WebhookEventFilterConfig,
    WebhookEventSourceConfig,
)
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    SecretRequest,
    SecretUpdate,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)

# -------------------- Utils -----------------------------------


class BitbucketEventType(StrEnum):
    """Collection of all possible Bitbucket Events."""

    PUSH_EVENT = "push_event"
    TAG_EVENT = "tag_event"


# -------------------- Bitbucket Event Models ----------------------------------


class User(BaseModel):
    """Bitbucket User."""

    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None


class Commit(BaseModel):
    """Bitbucket Commit."""

    hash: str
    message: str
    links: Dict[str, Any]
    author: User


class Repository(BaseModel):
    """Bitbucket Repository."""

    uuid: str
    name: str
    full_name: str
    links: Dict[str, Any]


class PushChange(BaseModel):
    """Bitbucket Push Change."""

    new: Optional[Dict[str, Any]] = None
    old: Optional[Dict[str, Any]] = None
    commits: List[Commit]


class Push(BaseModel):
    """Bitbucket Push."""

    changes: List[PushChange]


class BitbucketEvent(BaseEvent):
    """Bitbucket Event."""

    actor: User
    repository: Repository
    push: Push
    model_config = ConfigDict(extra="allow")

    @property
    def branch(self) -> Optional[str]:
        """The branch the event happened on.

        Returns:
            The branch name.
        """
        if self.push.changes[0].new:
            branch = self.push.changes[0].new.get("name", None)
            if self.push.changes[0].new.get("name", None):
                return str(branch)
        return None

    @property
    def event_type(self) -> Union[BitbucketEventType, str]:
        """The type of Bitbucket event.

        Returns:
            The type of the event.
        """
        is_push_event = all(
            [change.new is not None for change in self.push.changes]
        )
        is_tag_event = all(
            [
                change.new.get("type") == "tag"
                for change in self.push.changes
                if change.new
            ]
        )

        if is_push_event:
            return BitbucketEventType.PUSH_EVENT
        elif is_tag_event:
            return BitbucketEventType.TAG_EVENT
        else:
            return "unknown"


# -------------------- Configuration Models ----------------------------------


class BitbucketWebhookEventFilterConfiguration(WebhookEventFilterConfig):
    """Configuration for Bitbucket event filters."""

    repo: Optional[str] = None
    branch: Optional[str] = None
    event_type: Optional[BitbucketEventType] = None

    def event_matches_filter(self, event: BaseEvent) -> bool:
        """Checks the filter against the inbound event.

        Args:
            event: The incoming event

        Returns:
            Whether the event matches the filter
        """
        if not isinstance(event, BitbucketEvent):
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


class BitbucketWebhookEventSourceConfiguration(WebhookEventSourceConfig):
    """Configuration for Bitbucket source filters."""

    webhook_secret: Optional[str] = Field(
        default=None,
        title="The webhook secret for the event source.",
    )
    webhook_secret_id: Optional[UUID] = Field(
        default=None,
        description="The ID of the secret containing the webhook secret.",
    )
    rotate_secret: Optional[bool] = Field(
        default=None, description="Set to rotate the webhook secret."
    )


# -------------------- Bitbucket Webhook Plugin -----------------------------------


class BitbucketWebhookEventSourceHandler(BaseWebhookEventSourceHandler):
    """Handler for all Bitbucket events."""

    @property
    def config_class(self) -> Type[BitbucketWebhookEventSourceConfiguration]:
        """Returns the webhook event source configuration class.

        Returns:
            The configuration.
        """
        return BitbucketWebhookEventSourceConfiguration

    @property
    def filter_class(self) -> Type[BitbucketWebhookEventFilterConfiguration]:
        """Returns the webhook event filter configuration class.

        Returns:
            The event filter configuration class.
        """
        return BitbucketWebhookEventFilterConfiguration

    @property
    def flavor_class(self) -> Type[BaseWebhookEventSourceFlavor]:
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
        """
        from zenml.integrations.bitbucket.plugins.bitbucket_webhook_event_source_flavor import (
            BitbucketWebhookEventSourceFlavor,
        )

        return BitbucketWebhookEventSourceFlavor

    def _interpret_event(self, event: Dict[str, Any]) -> BitbucketEvent:
        """Converts the generic event body into a event-source specific pydantic model.

        Args:
            event: The generic event body

        Returns:
            An instance of the event source specific pydantic model.

        Raises:
            ValueError: If the event body can not be parsed into the pydantic model.
        """
        try:
            Bitbucket_event = BitbucketEvent(**event)
        except ValueError:
            raise ValueError("Event did not match the pydantic model.")
        else:
            return Bitbucket_event

    def _get_webhook_secret(
        self, event_source: EventSourceResponse
    ) -> Optional[str]:
        """Get the webhook secret for the event source.

        Args:
            event_source: The event source to retrieve the secret for.

        Returns:
            The webhook secret associated with the event source, or None if a
            secret is not applicable.

        Raises:
            AuthorizationException: If the secret value could not be retrieved.
        """
        # Temporary solution to get the secret value for the Event Source
        config = self.validate_event_source_configuration(
            event_source.configuration
        )
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        webhook_secret_id = config.webhook_secret_id
        if webhook_secret_id is None:
            raise AuthorizationException(
                f"Webhook secret ID is missing from the event source "
                f"configuration for event source '{event_source.id}'."
            )
        try:
            return self.zen_store.get_secret(
                secret_id=webhook_secret_id
            ).secret_values["webhook_secret"]
        except KeyError:
            logger.exception(
                f"Could not retrieve secret value for webhook secret id "
                f"'{webhook_secret_id}'"
            )
            raise AuthorizationException(
                "Could not retrieve webhook signature."
            )

    def _validate_event_source_request(
        self, event_source: EventSourceRequest, config: EventSourceConfig
    ) -> None:
        """Validate an event source request before it is created in the database.

        The `webhook_secret`, `webhook_secret_id`, and `rotate_secret`
        fields are not allowed in the request.

        Args:
            event_source: Event source request.
            config: Event source configuration instantiated from the request.

        Raises:
            ValueError: If any of the disallowed fields are present in the
                request.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        for field in ["webhook_secret", "webhook_secret_id", "rotate_secret"]:
            if getattr(config, field) is not None:
                raise ValueError(
                    f"The `{field}` field is not allowed in the event source "
                    "request."
                )

    def _process_event_source_request(
        self, event_source: EventSourceResponse, config: EventSourceConfig
    ) -> None:
        """Process an event source request after it is created in the database.

        Generates a webhook secret and stores it in a secret in the database,
        then attaches the secret ID to the event source configuration.

        Args:
            event_source: Newly created event source
            config: Event source configuration instantiated from the response.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        assert (
            event_source.user is not None
        ), "User is not set for event source"

        secret_key_value = random_str(12)
        webhook_secret = SecretRequest(
            name=f"event_source-{str(event_source.id)}-{random_str(4)}".lower(),
            values={"webhook_secret": secret_key_value},
            workspace=event_source.workspace.id,
            user=event_source.user.id,
            scope=SecretScope.WORKSPACE,
        )
        secret = self.zen_store.create_secret(webhook_secret)

        # Store the secret ID in the event source configuration in the database
        event_source_update = EventSourceUpdate.from_response(event_source)
        assert event_source_update.configuration is not None
        event_source_update.configuration["webhook_secret_id"] = str(secret.id)

        self.zen_store.update_event_source(
            event_source_id=event_source.id,
            event_source_update=event_source_update,
        )

        # Set the webhook secret in the configuration returned to the user
        config.webhook_secret = secret_key_value
        # Remove hidden field from the response
        config.rotate_secret = None
        config.webhook_secret_id = None

    def _validate_event_source_update(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        event_source_update: EventSourceUpdate,
        config_update: EventSourceConfig,
    ) -> None:
        """Validate an event source update before it is reflected in the database.

        Ensure the webhook secret ID is preserved in the updated event source
        configuration.

        Args:
            event_source: Original event source before the update.
            config: Event source configuration instantiated from the original
                event source.
            event_source_update: Event source update request.
            config_update: Event source configuration instantiated from the
                updated event source.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        assert isinstance(
            config_update, BitbucketWebhookEventSourceConfiguration
        )

        config_update.webhook_secret_id = config.webhook_secret_id

    def _process_event_source_update(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        previous_event_source: EventSourceResponse,
        previous_config: EventSourceConfig,
    ) -> None:
        """Process an event source after it is updated in the database.

        If the `rotate_secret` field is set to `True`, the webhook secret is
        rotated and the new secret ID is attached to the event source
        configuration.

        Args:
            event_source: Event source after the update.
            config: Event source configuration instantiated from the updated
                event source.
            previous_event_source: Original event source before the update.
            previous_config: Event source configuration instantiated from the
                original event source.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        assert isinstance(
            previous_config, BitbucketWebhookEventSourceConfiguration
        )
        assert config.webhook_secret_id is not None

        if config.rotate_secret:
            # In case the secret is being rotated
            secret_key_value = random_str(12)
            webhook_secret = SecretUpdate(
                values={"webhook_secret": secret_key_value}
            )
            self.zen_store.update_secret(
                secret_id=config.webhook_secret_id,
                secret_update=webhook_secret,
            )

            # Remove the `rotate_secret` field from the configuration stored
            # in the database
            event_source_update = EventSourceUpdate.from_response(event_source)
            assert event_source_update.configuration is not None
            event_source_update.configuration.pop("rotate_secret")
            self.zen_store.update_event_source(
                event_source_id=event_source.id,
                event_source_update=event_source_update,
            )

            # Set the new secret in the configuration returned to the user
            config.webhook_secret = secret_key_value

        # Remove hidden fields from the response
        config.rotate_secret = None
        config.webhook_secret_id = None

    def _process_event_source_delete(
        self,
        event_source: EventSourceResponse,
        config: EventSourceConfig,
        force: Optional[bool] = False,
    ) -> None:
        """Process an event source before it is deleted from the database.

        Deletes the associated secret from the database.

        Args:
            event_source: Event source before the deletion.
            config: Validated instantiated event source configuration before
                the deletion.
            force: Whether to force deprovision the event source.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        if config.webhook_secret_id is not None:
            try:
                self.zen_store.delete_secret(
                    secret_id=config.webhook_secret_id
                )
            except KeyError:
                pass

        # Remove hidden fields from the response
        config.rotate_secret = None
        config.webhook_secret_id = None

    def _process_event_source_response(
        self, event_source: EventSourceResponse, config: EventSourceConfig
    ) -> None:
        """Process an event source response before it is returned to the user.

        Removes hidden fields from the configuration.

        Args:
            event_source: Event source response.
            config: Event source configuration instantiated from the response.
        """
        assert isinstance(config, BitbucketWebhookEventSourceConfiguration)
        # Remove hidden fields from the response
        config.rotate_secret = None
        config.webhook_secret_id = None
        config.webhook_secret = None
