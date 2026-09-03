#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Slack Events API webhook provider."""

import hashlib
import hmac
import json
import logging
import time
from collections.abc import Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    TypedDict,
    cast,
)

from pydantic import BaseModel, Field, model_validator

from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    ParsedWebhookDelivery,
    ParsedWebhookEvent,
    WebhookAuthenticationError,
    WebhookConfiguration,
    WebhookIntakeResponse,
    WebhookPayloadError,
    WebhookTargetEvent,
    WebhookTriggerMatch,
    matches_string_filter,
)
from zenml.webhooks.providers.types import BuiltinWebhookType

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)

SLACK_SIGNATURE_HEADER = "x-slack-signature"
SLACK_REQUEST_TIMESTAMP_HEADER = "x-slack-request-timestamp"
SLACK_SIGNATURE_VERSION = "v0"
SLACK_TIMESTAMP_TOLERANCE_SECONDS = 5 * 60

SLACK_EVENT_CALLBACK = "event_callback"
SLACK_URL_VERIFICATION = "url_verification"
SLACK_APP_RATE_LIMITED = "app_rate_limited"


class SlackWebhookEventType(StrEnum):
    """Slack event types used during intake and semantic matching."""

    APP_MENTION = "app_mention"
    MESSAGE = "message"
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"
    MESSAGE_METADATA_POSTED = "message_metadata_posted"
    MESSAGE_METADATA_UPDATED = "message_metadata_updated"
    FILE_SHARED = "file_shared"


class SlackEventFilter(WebhookTargetEvent):
    """Base filters shared by Slack target events."""

    team_id: StringFilterOption = None
    channel_id: StringFilterOption = None
    user_id: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for shared Slack filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {"team_id": False, "channel_id": False, "user_id": False}


class AppMentionEventFilter(SlackEventFilter):
    """Filters for a Slack app mention."""

    type: Literal[SlackWebhookEventType.APP_MENTION] = (
        SlackWebhookEventType.APP_MENTION
    )
    text: StringFilterOption = None
    threaded: bool | None = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for app-mention filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {**super().get_prefix_matching_support(), "text": True}


class MessageEventFilter(SlackEventFilter):
    """Filters for a Slack message event."""

    type: Literal[SlackWebhookEventType.MESSAGE] = (
        SlackWebhookEventType.MESSAGE
    )
    channel_type: StringFilterOption = None
    text: StringFilterOption = None
    subtype: StringFilterOption = None
    include_subtypes: bool = False
    threaded: bool | None = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for message filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            **super().get_prefix_matching_support(),
            "channel_type": False,
            "text": True,
            "subtype": False,
        }

    @model_validator(mode="after")
    def validate_subtype_filters(self) -> "MessageEventFilter":
        """Reject competing broad and targeted subtype selection.

        Returns:
            The validated message event filter.

        Raises:
            ValueError: If all subtypes and named subtypes are both selected.
        """
        if self.include_subtypes and self.subtype is not None:
            raise ValueError(
                "Slack message filters cannot combine 'include_subtypes' "
                "with 'subtype'."
            )
        return self


class _ReactionEventFilter(SlackEventFilter):
    """Shared filters for a Slack reaction event."""

    reaction: StringFilterOption = None
    item_user_id: StringFilterOption = None
    item_type: StringFilterOption = None
    item_id: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for reaction filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            **super().get_prefix_matching_support(),
            "reaction": False,
            "item_user_id": False,
            "item_type": False,
            "item_id": False,
        }


class ReactionAddedEventFilter(_ReactionEventFilter):
    """Filters for a Slack reaction being added."""

    type: Literal[SlackWebhookEventType.REACTION_ADDED] = (
        SlackWebhookEventType.REACTION_ADDED
    )


class ReactionRemovedEventFilter(_ReactionEventFilter):
    """Filters for a Slack reaction being removed."""

    type: Literal[SlackWebhookEventType.REACTION_REMOVED] = (
        SlackWebhookEventType.REACTION_REMOVED
    )


class _MessageMetadataEventFilter(SlackEventFilter):
    """Shared filters for a Slack message-metadata event."""

    app_id: StringFilterOption = None
    bot_id: StringFilterOption = None
    metadata_event_type: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for message-metadata filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            **super().get_prefix_matching_support(),
            "app_id": False,
            "bot_id": False,
            "metadata_event_type": True,
        }


class MessageMetadataPostedEventFilter(_MessageMetadataEventFilter):
    """Filters for Slack message metadata being posted."""

    type: Literal[SlackWebhookEventType.MESSAGE_METADATA_POSTED] = (
        SlackWebhookEventType.MESSAGE_METADATA_POSTED
    )


class MessageMetadataUpdatedEventFilter(_MessageMetadataEventFilter):
    """Filters for Slack message metadata being updated."""

    type: Literal[SlackWebhookEventType.MESSAGE_METADATA_UPDATED] = (
        SlackWebhookEventType.MESSAGE_METADATA_UPDATED
    )


class FileSharedEventFilter(SlackEventFilter):
    """Filters for a Slack file being shared."""

    type: Literal[SlackWebhookEventType.FILE_SHARED] = (
        SlackWebhookEventType.FILE_SHARED
    )
    file_id: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix-matching support for file-share filters.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {**super().get_prefix_matching_support(), "file_id": False}


SlackWebhookEventFilter: TypeAlias = Annotated[
    AppMentionEventFilter
    | MessageEventFilter
    | ReactionAddedEventFilter
    | ReactionRemovedEventFilter
    | MessageMetadataPostedEventFilter
    | MessageMetadataUpdatedEventFilter
    | FileSharedEventFilter,
    Field(discriminator="type"),
]


class SlackWebhookConfiguration(WebhookConfiguration):
    """Typed configuration for a Slack webhook trigger."""

    target_events: list[SlackWebhookEventFilter] = Field(min_length=1)


class _SlackCommonEventFields(TypedDict):
    """Required fields shared by every supported Slack semantic event."""

    event_id: str
    team_id: str
    event_time: int
    event_ts: str


def _matches_bool(*, actual: bool, configured: bool | None) -> bool:
    """Match a boolean value against an optional configured filter.

    Args:
        actual: The value extracted from the Slack event.
        configured: The configured value, or `None` to match either value.

    Returns:
        Whether the value matches the configured filter.
    """
    return configured is None or actual is configured


class SlackSemanticEvent(BaseModel):
    """Provider event normalized for semantic trigger matching."""

    event_filter_type: ClassVar[type[SlackEventFilter]]

    event_id: str
    team_id: str
    event_time: int
    event_ts: str

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Match identifiers shared by all Slack semantic events.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether the event's team matches the target.
        """
        return matches_string_filter(
            actual=self.team_id, configured=target.team_id
        )


class SlackUserEvent(SlackSemanticEvent):
    """Base event with a required Slack user identifier."""

    user_id: str

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Match the required user identifier.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether the event's team and user match the target.
        """
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.user_id, configured=target.user_id
                ),
            )
        )


class SlackChannelEvent(SlackUserEvent):
    """Base event with a required Slack channel identifier."""

    channel_id: str

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Match the required channel identifier.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether the event's team, user, and channel match the target.
        """
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.channel_id, configured=target.channel_id
                ),
            )
        )


class SlackAppMentionEvent(SlackChannelEvent):
    """Normalized Slack app mention."""

    event_filter_type = AppMentionEventFilter
    type: Literal[SlackWebhookEventType.APP_MENTION] = (
        SlackWebhookEventType.APP_MENTION
    )
    text: str | None = None
    message_ts: str | None = None
    thread_ts: str | None = None

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Return whether this mention matches an app-mention target.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether this mention matches the target.
        """
        if not isinstance(target, AppMentionEventFilter):
            return False
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.text, configured=target.text
                ),
                _matches_bool(
                    actual=self.thread_ts is not None,
                    configured=target.threaded,
                ),
            )
        )


class SlackMessageEvent(SlackSemanticEvent):
    """Normalized Slack message event."""

    event_filter_type = MessageEventFilter
    type: Literal[SlackWebhookEventType.MESSAGE] = (
        SlackWebhookEventType.MESSAGE
    )
    user_id: str | None = None
    channel_id: str | None = None
    channel_type: str | None = None
    text: str | None = None
    subtype: str | None = None
    bot_authored: bool = False
    message_ts: str | None = None
    thread_ts: str | None = None

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Return whether this message matches a message target.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether this message matches the target.
        """
        if not isinstance(target, MessageEventFilter):
            return False
        if target.subtype is not None:
            subtype_matches = matches_string_filter(
                actual=self.subtype, configured=target.subtype
            )
        elif target.include_subtypes:
            subtype_matches = True
        else:
            subtype_matches = self.subtype is None and not self.bot_authored
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.user_id, configured=target.user_id
                ),
                matches_string_filter(
                    actual=self.channel_id, configured=target.channel_id
                ),
                matches_string_filter(
                    actual=self.channel_type, configured=target.channel_type
                ),
                matches_string_filter(
                    actual=self.text, configured=target.text
                ),
                subtype_matches,
                _matches_bool(
                    actual=self.thread_ts is not None,
                    configured=target.threaded,
                ),
            )
        )


class SlackReactionItem(BaseModel):
    """Normalized item referenced by a Slack reaction event."""

    type: Literal["message", "file", "file_comment"]
    id: str
    channel_id: str | None = None
    file_id: str | None = None


class SlackReactionEvent(SlackUserEvent):
    """Shared normalized fields for a Slack reaction event."""

    channel_id: str | None = None
    reaction: str
    item_user_id: str | None = None
    item: SlackReactionItem

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Return whether this reaction matches its reaction target.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether this reaction matches the target.
        """
        if not isinstance(target, self.event_filter_type):
            return False
        reaction_target = cast(_ReactionEventFilter, target)
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.channel_id, configured=target.channel_id
                ),
                matches_string_filter(
                    actual=self.reaction, configured=reaction_target.reaction
                ),
                matches_string_filter(
                    actual=self.item_user_id,
                    configured=reaction_target.item_user_id,
                ),
                matches_string_filter(
                    actual=self.item.type,
                    configured=reaction_target.item_type,
                ),
                matches_string_filter(
                    actual=self.item.id, configured=reaction_target.item_id
                ),
            )
        )


class SlackReactionAddedEvent(SlackReactionEvent):
    """Normalized Slack reaction-added event."""

    event_filter_type = ReactionAddedEventFilter
    type: Literal[SlackWebhookEventType.REACTION_ADDED] = (
        SlackWebhookEventType.REACTION_ADDED
    )


class SlackReactionRemovedEvent(SlackReactionEvent):
    """Normalized Slack reaction-removed event."""

    event_filter_type = ReactionRemovedEventFilter
    type: Literal[SlackWebhookEventType.REACTION_REMOVED] = (
        SlackWebhookEventType.REACTION_REMOVED
    )


class SlackMessageMetadata(BaseModel):
    """Structured metadata attached to a Slack message."""

    event_type: str
    event_payload: dict[str, Any]


class SlackMessageMetadataEvent(SlackChannelEvent):
    """Shared normalized fields for a Slack message-metadata event."""

    app_id: str
    bot_id: str | None = None
    message_ts: str
    metadata: SlackMessageMetadata

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Return whether this metadata event matches its typed target.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether this metadata event matches the target.
        """
        if not isinstance(target, self.event_filter_type):
            return False
        metadata_target = cast(_MessageMetadataEventFilter, target)
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.app_id, configured=metadata_target.app_id
                ),
                matches_string_filter(
                    actual=self.bot_id, configured=metadata_target.bot_id
                ),
                matches_string_filter(
                    actual=self.metadata.event_type,
                    configured=metadata_target.metadata_event_type,
                ),
            )
        )


class SlackMessageMetadataPostedEvent(SlackMessageMetadataEvent):
    """Normalized Slack message-metadata-posted event."""

    event_filter_type = MessageMetadataPostedEventFilter
    type: Literal[SlackWebhookEventType.MESSAGE_METADATA_POSTED] = (
        SlackWebhookEventType.MESSAGE_METADATA_POSTED
    )


class SlackMessageMetadataUpdatedEvent(SlackMessageMetadataEvent):
    """Normalized Slack message-metadata-updated event."""

    event_filter_type = MessageMetadataUpdatedEventFilter
    type: Literal[SlackWebhookEventType.MESSAGE_METADATA_UPDATED] = (
        SlackWebhookEventType.MESSAGE_METADATA_UPDATED
    )
    previous_metadata: SlackMessageMetadata


class SlackFileSharedEvent(SlackChannelEvent):
    """Normalized Slack file-shared event."""

    event_filter_type = FileSharedEventFilter
    type: Literal[SlackWebhookEventType.FILE_SHARED] = (
        SlackWebhookEventType.FILE_SHARED
    )
    file_id: str

    def matches(self, target: SlackWebhookEventFilter) -> bool:
        """Return whether this file share matches a file-share target.

        Args:
            target: The typed Slack target event.

        Returns:
            Whether this file share matches the target.
        """
        if not isinstance(target, FileSharedEventFilter):
            return False
        return all(
            (
                super().matches(target),
                matches_string_filter(
                    actual=self.file_id, configured=target.file_id
                ),
            )
        )


class SlackWebhookProvider(BaseWebhookProvider):
    """Provider for signed Slack Events API deliveries."""

    webhook_type = BuiltinWebhookType.SLACK
    configuration_class = SlackWebhookConfiguration

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate a Slack delivery using its exact raw body.

        Args:
            body: The raw request body.
            headers: The request headers.
            secret: The Slack app signing secret.

        Raises:
            WebhookAuthenticationError: If the request cannot be authenticated.
        """
        signature = headers.get(SLACK_SIGNATURE_HEADER)
        if not signature or not signature.startswith(
            f"{SLACK_SIGNATURE_VERSION}="
        ):
            raise WebhookAuthenticationError(
                f"Missing or malformed {SLACK_SIGNATURE_HEADER} header."
            )

        timestamp = headers.get(SLACK_REQUEST_TIMESTAMP_HEADER)
        if (
            not timestamp
            or not timestamp.isascii()
            or not timestamp.isdigit()
            or len(timestamp) > 20
        ):
            raise WebhookAuthenticationError(
                "Missing or malformed "
                f"{SLACK_REQUEST_TIMESTAMP_HEADER} header."
            )
        if (
            abs(time.time() - int(timestamp))
            > SLACK_TIMESTAMP_TOLERANCE_SECONDS
        ):
            raise WebhookAuthenticationError(
                "Slack request timestamp is outside the allowed tolerance."
            )

        signature_base = (
            f"{SLACK_SIGNATURE_VERSION}:{timestamp}:".encode() + body
        )
        expected = (
            f"{SLACK_SIGNATURE_VERSION}="
            + hmac.new(
                secret.encode(), signature_base, hashlib.sha256
            ).hexdigest()
        )
        if not hmac.compare_digest(signature, expected):
            raise WebhookAuthenticationError("Invalid webhook signature.")

    def parse_delivery(
        self, body: bytes, headers: Mapping[str, str]
    ) -> ParsedWebhookDelivery:
        """Parse a Slack event or control delivery.

        Args:
            body: The raw request body.
            headers: The request headers.

        Returns:
            The optional event and Slack-compatible response.

        Raises:
            WebhookPayloadError: If the Slack envelope is malformed.
        """
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WebhookPayloadError(
                "Request body must be valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise WebhookPayloadError(
                "Request body must contain a top-level JSON object."
            )

        delivery_type = payload.get("type")
        if delivery_type == SLACK_EVENT_CALLBACK:
            return self._parse_event_callback(payload)
        if delivery_type == SLACK_URL_VERIFICATION:
            challenge = payload.get("challenge")
            if not isinstance(challenge, str) or not challenge:
                raise WebhookPayloadError(
                    "Slack URL verification requires a non-empty challenge."
                )
            return ParsedWebhookDelivery(
                event=None,
                response=WebhookIntakeResponse(
                    status_code=200,
                    body=challenge,
                    media_type="text/plain",
                ),
            )
        if delivery_type == SLACK_APP_RATE_LIMITED:
            self._validate_rate_limited_delivery(payload)
            return ParsedWebhookDelivery(
                event=None,
                response=WebhookIntakeResponse(status_code=200),
            )
        raise WebhookPayloadError(
            "Unsupported Slack delivery type."
            if isinstance(delivery_type, str) and delivery_type
            else "Slack delivery requires a non-empty type."
        )

    def _parse_event_callback(
        self, payload: dict[str, Any]
    ) -> ParsedWebhookDelivery:
        """Parse one Slack event callback envelope.

        Args:
            payload: The parsed Slack envelope.

        Returns:
            The trusted provider-neutral event and response.

        Raises:
            WebhookPayloadError: If required event metadata is malformed.
        """
        event = payload.get("event")
        if not isinstance(event, dict):
            raise WebhookPayloadError(
                "Slack event callback requires an event object."
            )
        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise WebhookPayloadError(
                "Slack event callback requires a non-empty event type."
            )
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise WebhookPayloadError(
                "Slack event callback requires a non-empty event_id."
            )
        return ParsedWebhookDelivery(
            event=ParsedWebhookEvent(
                event_type=event_type,
                delivery_id=event_id,
                payload=payload,
            ),
            response=WebhookIntakeResponse(status_code=200),
        )

    @staticmethod
    def _validate_rate_limited_delivery(payload: Mapping[str, Any]) -> None:
        """Validate and log a Slack rate-limit notification.

        Args:
            payload: The parsed Slack control delivery.

        Raises:
            WebhookPayloadError: If required rate-limit fields are malformed.
        """
        team_id = payload.get("team_id")
        api_app_id = payload.get("api_app_id")
        minute_rate_limited = payload.get("minute_rate_limited")
        if not isinstance(team_id, str) or not team_id:
            raise WebhookPayloadError(
                "Slack rate-limit notification requires a non-empty team_id."
            )
        if not isinstance(api_app_id, str) or not api_app_id:
            raise WebhookPayloadError(
                "Slack rate-limit notification requires a non-empty api_app_id."
            )
        if not isinstance(minute_rate_limited, int) or isinstance(
            minute_rate_limited, bool
        ):
            raise WebhookPayloadError(
                "Slack rate-limit notification requires an integer "
                "minute_rate_limited."
            )
        logger.warning(
            "Slack Events API delivery is rate limited for team %s and app %s "
            "as of minute %s.",
            team_id,
            api_app_id,
            minute_rate_limited,
        )

    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Reject direct event parsing in favor of delivery parsing.

        Args:
            payload: The parsed Slack payload.
            headers: The request headers.

        Returns:
            This method never returns successfully.

        Raises:
            NotImplementedError: Always, because Slack has control deliveries.
        """
        raise NotImplementedError(
            "Slack deliveries must be parsed with parse_delivery()."
        )

    def _cast_runtime_targets(
        self, trigger: "WebhookTriggerResponse"
    ) -> list[SlackWebhookEventFilter]:
        """Load one trigger's targets while tolerating stale stored data.

        Args:
            trigger: The candidate Slack webhook trigger.

        Returns:
            The validated targets, or an empty list for defective stored data.
        """
        try:
            configuration = self.validate_configuration(trigger.configuration)
        except (TypeError, ValueError):
            logger.exception(
                "Skipping defective webhook trigger configuration %s",
                trigger.id,
            )
            return []
        return cast(SlackWebhookConfiguration, configuration).target_events

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> "WebhookTriggerMatch[WebhookTriggerResponse]":
        """Match candidates and return the parsed semantic event.

        Args:
            event: The trusted webhook event.
            candidates: Triggers selected by generic orchestration.

        Returns:
            The matching triggers and any parsed semantic event.
        """
        semantic = self.parse_semantic_event(event)
        if semantic is None:
            return WebhookTriggerMatch(triggers=[])
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            targets = self._cast_runtime_targets(trigger)
            if any(semantic.matches(target) for target in targets):
                matches.append(trigger)
        return WebhookTriggerMatch(
            triggers=matches,
            event=semantic.model_dump(mode="json"),
        )

    def parse_semantic_event(
        self, event: "WebhookEvent"
    ) -> SlackSemanticEvent | None:
        """Normalize a trusted Slack event for trigger matching.

        Args:
            event: The trusted Slack webhook event.

        Returns:
            The normalized supported event, or `None` if it is not matchable.
        """
        payload = event.payload.get("event")
        if not isinstance(payload, Mapping):
            return None
        common_fields = self._common_event_fields(event, payload)
        if common_fields is None:
            return None
        if event.event_type == SlackWebhookEventType.APP_MENTION:
            return self._parse_app_mention(payload, common_fields)
        if event.event_type == SlackWebhookEventType.MESSAGE:
            return self._parse_message(payload, common_fields)
        if event.event_type == SlackWebhookEventType.REACTION_ADDED:
            return self._parse_reaction(
                payload, common_fields, SlackReactionAddedEvent
            )
        if event.event_type == SlackWebhookEventType.REACTION_REMOVED:
            return self._parse_reaction(
                payload, common_fields, SlackReactionRemovedEvent
            )
        if event.event_type == SlackWebhookEventType.MESSAGE_METADATA_POSTED:
            fields = self._parse_message_metadata_fields(
                payload, common_fields
            )
            return (
                SlackMessageMetadataPostedEvent(**fields)
                if fields is not None
                else None
            )
        if event.event_type == SlackWebhookEventType.MESSAGE_METADATA_UPDATED:
            return self._parse_message_metadata_updated(payload, common_fields)
        if event.event_type == SlackWebhookEventType.FILE_SHARED:
            return self._parse_file_shared(payload, common_fields)
        return None

    def _parse_app_mention(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
    ) -> SlackAppMentionEvent | None:
        """Normalize an app-mention callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.

        Returns:
            The normalized mention, or `None` if it is not matchable.
        """
        channel_id = self._optional_string(payload.get("channel"))
        user_id = self._event_user_id(payload)
        if channel_id is None or user_id is None:
            return None
        if self._is_bot_message(payload):
            return None
        return SlackAppMentionEvent(
            **common_fields,
            channel_id=channel_id,
            user_id=user_id,
            text=self._optional_string(payload.get("text")),
            message_ts=self._optional_string(payload.get("ts")),
            thread_ts=self._optional_string(payload.get("thread_ts")),
        )

    def _parse_message(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
    ) -> SlackMessageEvent | None:
        """Normalize a Slack message callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.

        Returns:
            The normalized message event, or `None` if a regular message is
            missing its stable identity fields.
        """
        content = self._message_content(payload)
        user_id = self._event_user_id(payload, content)
        channel_id = self._optional_string(
            payload.get("channel")
        ) or self._optional_string(content.get("channel"))
        subtype = self._optional_string(payload.get("subtype"))
        bot_authored = self._is_bot_message(payload) or self._is_bot_message(
            content
        )
        message_ts = self._optional_string(
            content.get("ts")
        ) or self._optional_string(payload.get("deleted_ts"))
        if message_ts is None:
            message_ts = self._optional_string(payload.get("ts"))
        if (
            subtype is None
            and not bot_authored
            and (user_id is None or channel_id is None or message_ts is None)
        ):
            return None
        return SlackMessageEvent(
            **common_fields,
            user_id=user_id,
            channel_id=channel_id,
            channel_type=self._optional_string(payload.get("channel_type"))
            or self._optional_string(content.get("channel_type")),
            text=self._optional_string(content.get("text")),
            subtype=subtype,
            bot_authored=bot_authored,
            message_ts=message_ts,
            thread_ts=self._optional_string(content.get("thread_ts"))
            or self._optional_string(payload.get("thread_ts")),
        )

    def _parse_reaction(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
        event_class: type[SlackReactionEvent],
    ) -> SlackReactionEvent | None:
        """Normalize a reaction callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.
            event_class: The reaction semantic model to instantiate.

        Returns:
            The normalized reaction, or `None` if required fields are missing.
        """
        reaction = self._optional_string(payload.get("reaction"))
        user_id = self._event_user_id(payload)
        item_payload = payload.get("item")
        if (
            reaction is None
            or user_id is None
            or not isinstance(item_payload, Mapping)
        ):
            return None
        item = self._parse_reaction_item(item_payload)
        if item is None:
            return None
        return event_class(
            **common_fields,
            user_id=user_id,
            channel_id=item.channel_id,
            reaction=reaction,
            item_user_id=self._optional_string(payload.get("item_user")),
            item=item,
        )

    def _parse_reaction_item(
        self, payload: Mapping[str, Any]
    ) -> SlackReactionItem | None:
        """Normalize one documented Slack reaction item shape.

        Args:
            payload: The embedded Slack reaction item.

        Returns:
            The normalized item, or `None` for unknown or malformed shapes.
        """
        item_type = payload.get("type")
        if item_type == "message":
            item_id = self._optional_string(payload.get("ts"))
        elif item_type == "file":
            item_id = self._optional_string(payload.get("file"))
        elif item_type == "file_comment":
            item_id = self._optional_string(payload.get("file_comment"))
        else:
            return None
        if item_id is None:
            return None
        return SlackReactionItem(
            type=item_type,
            id=item_id,
            channel_id=self._optional_string(payload.get("channel")),
            file_id=self._optional_string(payload.get("file")),
        )

    def _parse_message_metadata_fields(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
    ) -> dict[str, Any] | None:
        """Extract normalized fields from a message-metadata callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.

        Returns:
            Semantic model fields, or `None` if required fields are missing.
        """
        channel_id = self._optional_string(payload.get("channel_id"))
        app_id = self._optional_string(payload.get("app_id"))
        user_id = self._event_user_id(payload)
        message_ts = self._optional_string(payload.get("message_ts"))
        metadata_payload = payload.get("metadata")
        if (
            channel_id is None
            or app_id is None
            or user_id is None
            or message_ts is None
            or not isinstance(metadata_payload, Mapping)
        ):
            return None
        metadata = self._parse_metadata(metadata_payload)
        if metadata is None:
            return None
        return {
            **common_fields,
            "user_id": user_id,
            "channel_id": channel_id,
            "app_id": app_id,
            "bot_id": self._optional_string(payload.get("bot_id")),
            "message_ts": message_ts,
            "metadata": metadata,
        }

    def _parse_message_metadata_updated(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
    ) -> SlackMessageMetadataUpdatedEvent | None:
        """Normalize a message-metadata-updated callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.

        Returns:
            The normalized update, or `None` if either metadata value is invalid.
        """
        fields = self._parse_message_metadata_fields(payload, common_fields)
        previous_payload = payload.get("previous_metadata")
        if fields is None or not isinstance(previous_payload, Mapping):
            return None
        previous_metadata = self._parse_metadata(previous_payload)
        if previous_metadata is None:
            return None
        return SlackMessageMetadataUpdatedEvent(
            **fields, previous_metadata=previous_metadata
        )

    def _parse_file_shared(
        self,
        payload: Mapping[str, Any],
        common_fields: _SlackCommonEventFields,
    ) -> SlackFileSharedEvent | None:
        """Normalize a file-shared callback.

        Args:
            payload: The inner Slack event payload.
            common_fields: Validated fields shared by all semantic events.

        Returns:
            The normalized file share, or `None` if required fields are missing.
        """
        channel_id = self._optional_string(payload.get("channel_id"))
        file_id = self._optional_string(payload.get("file_id"))
        user_id = self._event_user_id(payload)
        if channel_id is None or user_id is None or file_id is None:
            return None
        return SlackFileSharedEvent(
            **common_fields,
            channel_id=channel_id,
            user_id=user_id,
            file_id=file_id,
        )

    def _common_event_fields(
        self, event: "WebhookEvent", payload: Mapping[str, Any]
    ) -> _SlackCommonEventFields | None:
        """Extract metadata shared by normalized Slack events.

        Args:
            event: The trusted Slack webhook event.
            payload: The inner Slack event payload.

        Returns:
            Required common fields, or `None` if any field is missing.
        """
        event_id = self._optional_string(event.delivery_id)
        team_id = self._optional_string(
            event.payload.get("team_id")
        ) or self._optional_string(payload.get("team_id"))
        event_time = self._optional_int(event.payload.get("event_time"))
        event_ts = self._optional_string(payload.get("event_ts"))
        if (
            event_id is None
            or team_id is None
            or event_time is None
            or event_ts is None
        ):
            return None
        return {
            "event_id": event_id,
            "team_id": team_id,
            "event_time": event_time,
            "event_ts": event_ts,
        }

    @staticmethod
    def _parse_metadata(
        payload: Mapping[str, Any],
    ) -> SlackMessageMetadata | None:
        """Normalize structured Slack message metadata.

        Args:
            payload: The Slack metadata object.

        Returns:
            The normalized metadata, or `None` if it is malformed.
        """
        event_type = SlackWebhookProvider._optional_string(
            payload.get("event_type")
        )
        event_payload = payload.get("event_payload")
        if event_type is None or not isinstance(event_payload, Mapping):
            return None
        return SlackMessageMetadata(
            event_type=event_type,
            event_payload=dict(event_payload),
        )

    @staticmethod
    def _message_content(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Select the message object containing content fields.

        Args:
            payload: The inner Slack message event payload.

        Returns:
            The nested current or previous message when present, otherwise the
            event payload itself.
        """
        message = payload.get("message")
        if isinstance(message, Mapping):
            return message
        previous_message = payload.get("previous_message")
        if isinstance(previous_message, Mapping):
            return previous_message
        return payload

    @staticmethod
    def _event_user_id(
        payload: Mapping[str, Any],
        fallback: Mapping[str, Any] | None = None,
    ) -> str | None:
        """Extract a Slack user identifier from an event payload.

        Args:
            payload: The primary Slack event payload.
            fallback: An optional nested message payload.

        Returns:
            The first non-empty documented user identifier.
        """
        user_id = SlackWebhookProvider._optional_string(
            payload.get("user")
        ) or SlackWebhookProvider._optional_string(payload.get("user_id"))
        if user_id is not None or fallback is None:
            return user_id
        return SlackWebhookProvider._optional_string(
            fallback.get("user")
        ) or SlackWebhookProvider._optional_string(fallback.get("user_id"))

    @staticmethod
    def _is_bot_message(payload: Mapping[str, Any]) -> bool:
        """Return whether a Slack message payload was authored by a bot.

        Args:
            payload: The inner Slack event payload.

        Returns:
            Whether Slack identifies the message as bot-authored.
        """
        return any(
            (
                SlackWebhookProvider._optional_string(payload.get("bot_id"))
                is not None,
                isinstance(payload.get("bot_profile"), Mapping),
                payload.get("subtype") == "bot_message",
            )
        )

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        """Return a non-empty string or `None` for optional metadata.

        Args:
            value: The untrusted payload value.

        Returns:
            The value if it is a non-empty string, otherwise `None`.
        """
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        """Return a non-boolean integer or `None` for optional metadata.

        Args:
            value: The untrusted payload value.

        Returns:
            The value if it is an integer, otherwise `None`.
        """
        return (
            value
            if isinstance(value, int) and not isinstance(value, bool)
            else None
        )
