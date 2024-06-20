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
"""Base class for event hub implementations."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from zenml import EventSourceResponse
from zenml.config.global_config import GlobalConfiguration
from zenml.event_sources.base_event import (
    BaseEvent,
)
from zenml.logger import get_logger
from zenml.models import (
    TriggerExecutionRequest,
    TriggerExecutionResponse,
    TriggerResponse,
)
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.jwt import JWTToken

if TYPE_CHECKING:
    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

ActionHandlerCallback = Callable[
    [Dict[str, Any], TriggerExecutionResponse, AuthContext], None
]


class BaseEventHub(ABC):
    """Base class for event hub implementations.

    The event hub is responsible for relaying events from event sources to
    action handlers. It functions similarly to a pub/sub system where
    event source handlers publish events and action handlers subscribe to them.

    The event hub also serves to decouple event sources from action handlers,
    allowing them to be configured independently and their implementations to be
    unaware of each other.
    """

    action_handlers: Dict[Tuple[str, str], ActionHandlerCallback] = {}

    @property
    def zen_store(self) -> "SqlZenStore":
        """Returns the active zen store.

        Returns:
            The active zen store.

        Raises:
            ValueError: If the active zen store is not a SQL zen store.
        """
        from zenml.zen_stores.sql_zen_store import SqlZenStore

        zen_store = GlobalConfiguration().zen_store

        if not isinstance(zen_store, SqlZenStore):
            raise ValueError("The event hub requires a SQL zen store.")

        return zen_store

    def subscribe_action_handler(
        self,
        action_flavor: str,
        action_subtype: str,
        callback: ActionHandlerCallback,
    ) -> None:
        """Subscribe an action handler to the event hub.

        Args:
            action_flavor: the flavor of the action to trigger.
            action_subtype: the subtype of the action to trigger.
            callback: the action to trigger when the trigger is activated.
        """
        self.action_handlers[(action_flavor, action_subtype)] = callback

    def unsubscribe_action_handler(
        self,
        action_flavor: str,
        action_subtype: str,
    ) -> None:
        """Unsubscribe an action handler from the event hub.

        Args:
            action_flavor: the flavor of the action to trigger.
            action_subtype: the subtype of the action to trigger.
        """
        self.action_handlers.pop((action_flavor, action_subtype), None)

    def trigger_action(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
        trigger: TriggerResponse,
        action_callback: ActionHandlerCallback,
    ) -> None:
        """Trigger an action.

        Args:
            event: The event.
            event_source: The event source that produced the event.
            trigger: The trigger that was activated.
            action_callback: The action to trigger.
        """
        request = TriggerExecutionRequest(
            trigger=trigger.id, event_metadata=event.model_dump()
        )

        action_config = trigger.action.configuration

        trigger_execution = self.zen_store.create_trigger_execution(request)

        # Generate an API token that can be used by external workloads
        # implementing the action to authenticate with the server. This token
        # is associated with the service account configured for the trigger
        # and has a validity defined by the trigger's authentication window.
        token = JWTToken(
            user_id=trigger.action.service_account.id,
        )
        expires: Optional[datetime] = None
        if trigger.action.auth_window:
            expires = datetime.utcnow() + timedelta(
                minutes=trigger.action.auth_window
            )
        encoded_token = token.encode(expires=expires)
        auth_context = AuthContext(
            user=trigger.action.service_account,
            access_token=token,
            encoded_access_token=encoded_token,
        )

        try:
            # TODO: We need to make this async, as this might take quite some
            # time per trigger. We can either use threads starting here, or
            # use fastapi background tasks that get passed here instead of
            # running the event hub as a background tasks in the webhook
            # endpoints
            action_callback(
                action_config,
                trigger_execution,
                auth_context,
            )
        except Exception:
            # Don't let action errors stop the event hub from working
            logger.exception(
                f"An error occurred while executing trigger {trigger}."
            )

    @abstractmethod
    def activate_trigger(self, trigger: TriggerResponse) -> None:
        """Add a trigger to the event hub.

        Configure the event hub to trigger an action when an event is received.

        Args:
            trigger: the trigger to activate.
        """

    @abstractmethod
    def deactivate_trigger(self, trigger: TriggerResponse) -> None:
        """Remove a trigger from the event hub.

        Configure the event hub to stop triggering an action when an event is
        received.

        Args:
            trigger: the trigger to deactivate.
        """

    @abstractmethod
    def publish_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> None:
        """Publish an event to the event hub.

        Args:
            event: The event.
            event_source: The event source that produced the event.
        """
