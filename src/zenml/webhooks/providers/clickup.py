#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""ClickUp webhook provider and semantic target event catalog."""

import json
import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from pydantic import Field

from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookTargetEvent,
    authenticate_hmac_sha256_hex,
)
from zenml.webhooks.providers.types import BuiltinWebhookType

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)

CLICKUP_SIGNATURE_HEADER = "x-signature"

_RESOURCE_KEYS = ("task_id", "list_id", "folder_id", "space_id")


class ClickUpWebhookEvent(StrEnum):
    """ClickUp events supported by webhook triggers."""

    TASK_CREATED = "taskCreated"
    TASK_UPDATED = "taskUpdated"
    TASK_DELETED = "taskDeleted"
    TASK_STATUS_UPDATED = "taskStatusUpdated"
    TASK_MOVED = "taskMoved"
    TASK_ASSIGNEE_UPDATED = "taskAssigneeUpdated"
    TASK_COMMENT_POSTED = "taskCommentPosted"
    LIST_CREATED = "listCreated"
    LIST_UPDATED = "listUpdated"
    LIST_DELETED = "listDeleted"


class ClickUpTargetEvent(WebhookTargetEvent):
    """Filters for a ClickUp webhook event."""

    type: ClickUpWebhookEvent
    list_id: StringFilterOption = None
    task_id: StringFilterOption = None
    space_id: StringFilterOption = None
    folder_id: StringFilterOption = None
    status: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix matching support for string filter fields.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            "list_id": False,
            "task_id": False,
            "space_id": False,
            "folder_id": False,
            "status": False,
        }


class ClickUpWebhookConfiguration(WebhookConfiguration):
    """Typed configuration for a ClickUp webhook trigger."""

    target_events: list[ClickUpTargetEvent] = Field(min_length=1)


def _matches_string_filter(
    *, actual: str | None, configured: str | list[str] | None
) -> bool:
    """Match an extracted value against a supported string filter.

    Args:
        actual: The value extracted from the webhook event.
        configured: The configured exact, prefix, or alternatives filter.

    Returns:
        Whether the extracted value matches the configured filter.
    """
    if configured is None:
        return True

    if actual is None:
        return False
    
    values = configured if isinstance(configured, list) else [configured]
    for value in values:
        if value.startswith("oneof:"):
            if actual in json.loads(value.removeprefix("oneof:")):
                return True
        elif actual == value:
            return True
    return False


def _id_string(payload: Mapping[str, Any], key: str) -> str | None:
    """Extract an ID string from a ClickUp payload.

    Args:
        payload: The ClickUp payload.
        key: The key to extract the ID from.

    Returns:
        The ID string, or `None` if the key is missing or empty.
    """
    value = payload.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (str, int)) and str(value):
        return str(value)
    return None


def _history_item_ids(payload: Mapping[str, Any]) -> list[str]:
    """Extract history item IDs from a ClickUp payload.

    Args:
        payload: The ClickUp payload.

    Returns:
        The history item IDs, or an empty list if the history items are missing or empty.
    """
    items = payload.get("history_items")
    if not isinstance(items, list):
        return []
    ids: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        item_id = item.get("id")
        if isinstance(item_id, (str, int)) and str(item_id):
            ids.append(str(item_id))
    return sorted(ids)


def _status_after(payload: Mapping[str, Any]) -> str | None:
    """Extract the status after a change from a ClickUp payload.

    Args:
        payload: The ClickUp payload.

    Returns:
        The status after the change, or `None` if the history items are missing or empty.
    """
    items = payload.get("history_items")
    if not isinstance(items, list) or not items:
        return None
    last = items[-1]
    if not isinstance(last, Mapping):
        return None
    after = last.get("after")
    if isinstance(after, str) and after:
        return after
    if isinstance(after, Mapping):
        status = after.get("status")
        if isinstance(status, str) and status:
            return status
    return None


class ClickUpSemanticEvent:
    """Normalized ClickUp event used for trigger matching."""

    def __init__(
        self,
        *,
        event_type: ClickUpWebhookEvent,
        list_id: str | None,
        task_id: str | None,
        space_id: str | None,
        folder_id: str | None,
        status: str | None,
    ) -> None:
        """Initialize one normalized ClickUp event.

        Args:
            event_type: The ClickUp event name.
            list_id: The list ID, if present.
            task_id: The task ID, if present.
            space_id: The space ID, if present.
            folder_id: The folder ID, if present.
            status: The status after the change, if present.
        """
        self.event_type = event_type
        self.list_id = list_id
        self.task_id = task_id
        self.space_id = space_id
        self.folder_id = folder_id
        self.status = status

    def matches(self, target: ClickUpTargetEvent) -> bool:
        """Return whether this event matches a typed target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
        if self.event_type != target.type:
            return False
        return all(
            (
                _matches_string_filter(
                    actual=self.list_id, configured=target.list_id
                ),
                _matches_string_filter(
                    actual=self.task_id, configured=target.task_id
                ),
                _matches_string_filter(
                    actual=self.space_id, configured=target.space_id
                ),
                _matches_string_filter(
                    actual=self.folder_id, configured=target.folder_id
                ),
                _matches_string_filter(
                    actual=self.status, configured=target.status
                ),
            )
        )


class ClickUpWebhookProvider(BaseWebhookProvider):
    """Provider for authenticated and semantically matched ClickUp webhooks."""

    webhook_type = BuiltinWebhookType.CLICKUP
    configuration_class = ClickUpWebhookConfiguration

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate a ClickUp delivery.

        Args:
            body: The exact raw request body.
            headers: The request headers.
            secret: The webhook signing secret.
        """
        authenticate_hmac_sha256_hex(
            body=body,
            headers=headers,
            secret=secret,
            header=CLICKUP_SIGNATURE_HEADER,
        )

    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Extract the ClickUp event name from the JSON body.

        Args:
            payload: The parsed ClickUp payload.
            headers: The request headers.

        Returns:
            The ClickUp event name.

        Raises:
            WebhookPayloadError: If the event field is missing or empty.
        """
        event_type = payload.get("event")
        if not isinstance(event_type, str) or not event_type:
            raise WebhookPayloadError(
                "Missing or empty ClickUp 'event' field."
            )
        return event_type

    def get_delivery_id(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str | None:
        """Build ClickUp's documented idempotency key.

        Args:
            payload: The parsed ClickUp payload.
            headers: The request headers.

        Returns:
            The delivery ID, if the payload contains a webhook ID.

        Raises:
            WebhookPayloadError: If webhook_id is missing.
        """
        webhook_id = payload.get("webhook_id")
        if not isinstance(webhook_id, str) or not webhook_id:
            raise WebhookPayloadError(
                "Missing or empty ClickUp 'webhook_id' field."
            )
        history_ids = _history_item_ids(payload)
        if history_ids:
            return f"{webhook_id}:{','.join(history_ids)}"
        resource_id = next(
            (
                value
                for key in _RESOURCE_KEYS
                if (value := _id_string(payload, key)) is not None
            ),
            "unknown",
        )
        event_type = payload.get("event")
        event_name = event_type if isinstance(event_type, str) else "unknown"
        return f"{webhook_id}:{event_name}:{resource_id}"

    def _cast_runtime_targets(
        self, trigger: "WebhookTriggerResponse"
    ) -> list[ClickUpTargetEvent]:
        """Cast a webhook trigger configuration to a list of target events.

        Args:
            trigger: The webhook trigger configuration.

        Returns:
            The list of target events.
        """
        try:
            configuration = self.validate_configuration(trigger.configuration)
        except (TypeError, ValueError):
            logger.exception(
                "Skipping defective webhook trigger configuration %s",
                trigger.id,
            )
            return []
        return cast(ClickUpWebhookConfiguration, configuration).target_events

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> list["WebhookTriggerResponse"]:
        """Match ClickUp candidates while tolerating stale stored entries.

        Args:
            event: The trusted ClickUp webhook event.
            candidates: The candidate webhook triggers.

        Returns:
            The candidates matching the semantic event.
        """
        semantic = self.parse_semantic_event(event)
        if semantic is None:
            return []
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            targets = self._cast_runtime_targets(trigger)
            if any(semantic.matches(target) for target in targets):
                matches.append(trigger)
        return matches

    def parse_semantic_event(
        self, event: "WebhookEvent"
    ) -> ClickUpSemanticEvent | None:
        """Parse a trusted delivery into a normalized semantic event.

        Args:
            event: The trusted ClickUp webhook event.

        Returns:
            The normalized semantic event, or `None` for unsupported events.
        """
        try:
            event_type = ClickUpWebhookEvent(event.event_type)
        except ValueError:
            return None
        payload = event.payload
        return ClickUpSemanticEvent(
            event_type=event_type,
            list_id=_id_string(payload, "list_id"),
            task_id=_id_string(payload, "task_id"),
            space_id=_id_string(payload, "space_id"),
            folder_id=_id_string(payload, "folder_id"),
            status=_status_after(payload),
        )
