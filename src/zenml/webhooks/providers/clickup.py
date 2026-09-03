#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""ClickUp webhook provider and semantic target event catalog."""

import json
import logging
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    cast,
)

from pydantic import BaseModel, Field

from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookTargetEvent,
    WebhookTriggerMatch,
    authenticate_hmac_sha256,
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


class _ClickUpListTarget(WebhookTargetEvent):
    """Shared location filters for ClickUp list events."""

    list_id: StringFilterOption = None
    space_id: StringFilterOption = None
    folder_id: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix matching support for string filter fields.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            "list_id": False,
            "space_id": False,
            "folder_id": False,
        }


class _ClickUpTaskTarget(_ClickUpListTarget):
    """Shared location and task filters for ClickUp task events."""

    task_id: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix matching support for string filter fields.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            **super().get_prefix_matching_support(),
            "task_id": False,
        }


class _ClickUpTaskStatusTarget(_ClickUpTaskTarget):
    """Task filters plus the post-change status."""

    status: StringFilterOption = None

    @classmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix matching support for string filter fields.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """
        return {
            **super().get_prefix_matching_support(),
            "status": False,
        }


class TaskCreated(_ClickUpTaskTarget):
    """Filters for a created ClickUp task."""

    type: Literal[ClickUpWebhookEvent.TASK_CREATED] = (
        ClickUpWebhookEvent.TASK_CREATED
    )


class TaskUpdated(_ClickUpTaskTarget):
    """Filters for an updated ClickUp task."""

    type: Literal[ClickUpWebhookEvent.TASK_UPDATED] = (
        ClickUpWebhookEvent.TASK_UPDATED
    )


class TaskDeleted(_ClickUpTaskTarget):
    """Filters for a deleted ClickUp task."""

    type: Literal[ClickUpWebhookEvent.TASK_DELETED] = (
        ClickUpWebhookEvent.TASK_DELETED
    )


class TaskStatusUpdated(_ClickUpTaskStatusTarget):
    """Filters for a ClickUp task status change."""

    type: Literal[ClickUpWebhookEvent.TASK_STATUS_UPDATED] = (
        ClickUpWebhookEvent.TASK_STATUS_UPDATED
    )


class TaskMoved(_ClickUpTaskTarget):
    """Filters for a ClickUp task moved to another list."""

    type: Literal[ClickUpWebhookEvent.TASK_MOVED] = (
        ClickUpWebhookEvent.TASK_MOVED
    )


class TaskAssigneeUpdated(_ClickUpTaskTarget):
    """Filters for a ClickUp task assignee change."""

    type: Literal[ClickUpWebhookEvent.TASK_ASSIGNEE_UPDATED] = (
        ClickUpWebhookEvent.TASK_ASSIGNEE_UPDATED
    )


class TaskCommentPosted(_ClickUpTaskTarget):
    """Filters for a comment posted on a ClickUp task."""

    type: Literal[ClickUpWebhookEvent.TASK_COMMENT_POSTED] = (
        ClickUpWebhookEvent.TASK_COMMENT_POSTED
    )


class ListCreated(_ClickUpListTarget):
    """Filters for a created ClickUp list."""

    type: Literal[ClickUpWebhookEvent.LIST_CREATED] = (
        ClickUpWebhookEvent.LIST_CREATED
    )


class ListUpdated(_ClickUpListTarget):
    """Filters for an updated ClickUp list."""

    type: Literal[ClickUpWebhookEvent.LIST_UPDATED] = (
        ClickUpWebhookEvent.LIST_UPDATED
    )


class ListDeleted(_ClickUpListTarget):
    """Filters for a deleted ClickUp list."""

    type: Literal[ClickUpWebhookEvent.LIST_DELETED] = (
        ClickUpWebhookEvent.LIST_DELETED
    )


ClickUpWebhookTargetEvent: TypeAlias = Annotated[
    TaskCreated
    | TaskUpdated
    | TaskDeleted
    | TaskStatusUpdated
    | TaskMoved
    | TaskAssigneeUpdated
    | TaskCommentPosted
    | ListCreated
    | ListUpdated
    | ListDeleted,
    Field(discriminator="type"),
]


class ClickUpWebhookConfiguration(WebhookConfiguration):
    """Typed configuration for a ClickUp webhook trigger."""

    target_events: list[ClickUpWebhookTargetEvent] = Field(min_length=1)


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


def _matches_location_filters(
    *,
    list_id: str | None,
    space_id: str | None,
    folder_id: str | None,
    target: _ClickUpListTarget,
) -> bool:
    """Match shared ClickUp location filters.

    Args:
        list_id: The list ID extracted from the payload.
        space_id: The space ID extracted from the payload.
        folder_id: The folder ID extracted from the payload.
        target: The typed target event configuration.

    Returns:
        Whether the extracted location matches the target filters.
    """
    return all(
        (
            _matches_string_filter(actual=list_id, configured=target.list_id),
            _matches_string_filter(
                actual=space_id, configured=target.space_id
            ),
            _matches_string_filter(
                actual=folder_id, configured=target.folder_id
            ),
        )
    )


def _matches_task_filters(
    *,
    task_id: str | None,
    list_id: str | None,
    space_id: str | None,
    folder_id: str | None,
    target: _ClickUpTaskTarget,
) -> bool:
    """Match shared ClickUp task and location filters.

    Args:
        task_id: The task ID extracted from the payload.
        list_id: The list ID extracted from the payload.
        space_id: The space ID extracted from the payload.
        folder_id: The folder ID extracted from the payload.
        target: The typed target event configuration.

    Returns:
        Whether the extracted task matches the target filters.
    """
    return all(
        (
            _matches_string_filter(actual=task_id, configured=target.task_id),
            _matches_location_filters(
                list_id=list_id,
                space_id=space_id,
                folder_id=folder_id,
                target=target,
            ),
        )
    )


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
        The history item IDs, or an empty list if they are missing.
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
        The status after the change, or `None` if it is missing.
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


class ClickUpSemanticEvent(BaseModel):
    """Normalized ClickUp event used for trigger matching."""

    event_filter_type: ClassVar[type[WebhookTargetEvent]]
    type: str

    @abstractmethod
    def matches(self, target: ClickUpWebhookTargetEvent) -> bool:
        """Return whether the semantic event matches its typed target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether the semantic event matches the target.
        """


class ClickUpTaskSemanticEvent(ClickUpSemanticEvent):
    """Normalized ClickUp task event with shared location filters."""

    event_filter_type: ClassVar[type[_ClickUpTaskTarget]]
    task_id: str | None = None
    list_id: str | None = None
    space_id: str | None = None
    folder_id: str | None = None

    def matches(self, target: ClickUpWebhookTargetEvent) -> bool:
        """Return whether this event matches a typed task target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
        if not isinstance(target, self.event_filter_type):
            return False
        return _matches_task_filters(
            task_id=self.task_id,
            list_id=self.list_id,
            space_id=self.space_id,
            folder_id=self.folder_id,
            target=target,
        )


class ClickUpListSemanticEvent(ClickUpSemanticEvent):
    """Normalized ClickUp list event with shared location filters."""

    event_filter_type: ClassVar[type[_ClickUpListTarget]]
    list_id: str | None = None
    space_id: str | None = None
    folder_id: str | None = None

    def matches(self, target: ClickUpWebhookTargetEvent) -> bool:
        """Return whether this event matches a typed list target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
        if not isinstance(target, self.event_filter_type):
            return False
        return _matches_location_filters(
            list_id=self.list_id,
            space_id=self.space_id,
            folder_id=self.folder_id,
            target=target,
        )


class ClickUpTaskCreatedEvent(ClickUpTaskSemanticEvent):
    """Normalized created-task event."""

    event_filter_type = TaskCreated
    type: Literal[ClickUpWebhookEvent.TASK_CREATED] = (
        ClickUpWebhookEvent.TASK_CREATED
    )


class ClickUpTaskUpdatedEvent(ClickUpTaskSemanticEvent):
    """Normalized updated-task event."""

    event_filter_type = TaskUpdated
    type: Literal[ClickUpWebhookEvent.TASK_UPDATED] = (
        ClickUpWebhookEvent.TASK_UPDATED
    )


class ClickUpTaskDeletedEvent(ClickUpTaskSemanticEvent):
    """Normalized deleted-task event."""

    event_filter_type = TaskDeleted
    type: Literal[ClickUpWebhookEvent.TASK_DELETED] = (
        ClickUpWebhookEvent.TASK_DELETED
    )


class ClickUpTaskStatusUpdatedEvent(ClickUpTaskSemanticEvent):
    """Normalized task-status-updated event."""

    event_filter_type = TaskStatusUpdated
    type: Literal[ClickUpWebhookEvent.TASK_STATUS_UPDATED] = (
        ClickUpWebhookEvent.TASK_STATUS_UPDATED
    )
    status: str | None = None

    def matches(self, target: ClickUpWebhookTargetEvent) -> bool:
        """Return whether this event matches a status-updated target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
        if not isinstance(target, TaskStatusUpdated):
            return False
        return all(
            (
                _matches_task_filters(
                    task_id=self.task_id,
                    list_id=self.list_id,
                    space_id=self.space_id,
                    folder_id=self.folder_id,
                    target=target,
                ),
                _matches_string_filter(
                    actual=self.status, configured=target.status
                ),
            )
        )


class ClickUpTaskMovedEvent(ClickUpTaskSemanticEvent):
    """Normalized moved-task event."""

    event_filter_type = TaskMoved
    type: Literal[ClickUpWebhookEvent.TASK_MOVED] = (
        ClickUpWebhookEvent.TASK_MOVED
    )


class ClickUpTaskAssigneeUpdatedEvent(ClickUpTaskSemanticEvent):
    """Normalized task-assignee-updated event."""

    event_filter_type = TaskAssigneeUpdated
    type: Literal[ClickUpWebhookEvent.TASK_ASSIGNEE_UPDATED] = (
        ClickUpWebhookEvent.TASK_ASSIGNEE_UPDATED
    )


class ClickUpTaskCommentPostedEvent(ClickUpTaskSemanticEvent):
    """Normalized task-comment-posted event."""

    event_filter_type = TaskCommentPosted
    type: Literal[ClickUpWebhookEvent.TASK_COMMENT_POSTED] = (
        ClickUpWebhookEvent.TASK_COMMENT_POSTED
    )


class ClickUpListCreatedEvent(ClickUpListSemanticEvent):
    """Normalized created-list event."""

    event_filter_type = ListCreated
    type: Literal[ClickUpWebhookEvent.LIST_CREATED] = (
        ClickUpWebhookEvent.LIST_CREATED
    )


class ClickUpListUpdatedEvent(ClickUpListSemanticEvent):
    """Normalized updated-list event."""

    event_filter_type = ListUpdated
    type: Literal[ClickUpWebhookEvent.LIST_UPDATED] = (
        ClickUpWebhookEvent.LIST_UPDATED
    )


class ClickUpListDeletedEvent(ClickUpListSemanticEvent):
    """Normalized deleted-list event."""

    event_filter_type = ListDeleted
    type: Literal[ClickUpWebhookEvent.LIST_DELETED] = (
        ClickUpWebhookEvent.LIST_DELETED
    )


_TASK_SEMANTIC_EVENTS: Mapping[
    ClickUpWebhookEvent, type[ClickUpTaskSemanticEvent]
] = {
    ClickUpWebhookEvent.TASK_CREATED: ClickUpTaskCreatedEvent,
    ClickUpWebhookEvent.TASK_UPDATED: ClickUpTaskUpdatedEvent,
    ClickUpWebhookEvent.TASK_DELETED: ClickUpTaskDeletedEvent,
    ClickUpWebhookEvent.TASK_STATUS_UPDATED: ClickUpTaskStatusUpdatedEvent,
    ClickUpWebhookEvent.TASK_MOVED: ClickUpTaskMovedEvent,
    ClickUpWebhookEvent.TASK_ASSIGNEE_UPDATED: ClickUpTaskAssigneeUpdatedEvent,
    ClickUpWebhookEvent.TASK_COMMENT_POSTED: ClickUpTaskCommentPostedEvent,
}

_LIST_SEMANTIC_EVENTS: Mapping[
    ClickUpWebhookEvent, type[ClickUpListSemanticEvent]
] = {
    ClickUpWebhookEvent.LIST_CREATED: ClickUpListCreatedEvent,
    ClickUpWebhookEvent.LIST_UPDATED: ClickUpListUpdatedEvent,
    ClickUpWebhookEvent.LIST_DELETED: ClickUpListDeletedEvent,
}


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
        authenticate_hmac_sha256(
            body=body,
            headers=headers,
            secret=secret,
            header=CLICKUP_SIGNATURE_HEADER,
            prefixed=False,
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
    ) -> list[ClickUpWebhookTargetEvent]:
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
    ) -> "WebhookTriggerMatch[WebhookTriggerResponse]":
        """Match ClickUp triggers and return the parsed semantic event.

        Args:
            event: The trusted ClickUp webhook event.
            candidates: The candidate webhook triggers.

        Returns:
            Matching triggers and their shared semantic event.
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
        list_id = _id_string(payload, "list_id")
        space_id = _id_string(payload, "space_id")
        folder_id = _id_string(payload, "folder_id")
        task_cls = _TASK_SEMANTIC_EVENTS.get(event_type)
        if task_cls is ClickUpTaskStatusUpdatedEvent:
            return ClickUpTaskStatusUpdatedEvent(
                type=event_type,
                task_id=_id_string(payload, "task_id"),
                list_id=list_id,
                space_id=space_id,
                folder_id=folder_id,
                status=_status_after(payload),
            )
        if task_cls is not None:
            return task_cls(
                type=event_type,
                task_id=_id_string(payload, "task_id"),
                list_id=list_id,
                space_id=space_id,
                folder_id=folder_id,
            )
        list_cls = _LIST_SEMANTIC_EVENTS.get(event_type)
        if list_cls is not None:
            return list_cls(
                type=event_type,
                list_id=list_id,
                space_id=space_id,
                folder_id=folder_id,
            )
        return None
