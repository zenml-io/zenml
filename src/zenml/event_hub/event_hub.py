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
"""Base class for all the Event Hub."""

from typing import List

from pydantic import ValidationError

from zenml import EventSourceResponse
from zenml.enums import PluginType
from zenml.event_hub.base_event_hub import BaseEventHub
from zenml.event_sources.base_event import (
    BaseEvent,
)
from zenml.event_sources.base_event_source import (
    BaseEventSourceFlavor,
)
from zenml.logger import get_logger
from zenml.models import (
    TriggerFilter,
    TriggerResponse,
)
from zenml.utils.pagination_utils import depaginate
from zenml.zen_server.utils import plugin_flavor_registry

logger = get_logger(__name__)


class InternalEventHub(BaseEventHub):
    """Internal in-server event hub implementation.

    The internal in-server event hub uses the database as a source of truth for
    configured triggers and triggers actions by calling the action handlers
    directly.
    """

    def activate_trigger(self, trigger: TriggerResponse) -> None:
        """Add a trigger to the event hub.

        Configure the event hub to trigger an action when an event is received.

        Args:
            trigger: the trigger to activate.
        """
        # We don't need to do anything here to change the event hub
        # configuration. The in-server event hub already uses the database
        # as the source of truth regarding configured active triggers.

    def deactivate_trigger(self, trigger: TriggerResponse) -> None:
        """Remove a trigger from the event hub.

        Configure the event hub to stop triggering an action when an event is
        received.

        Args:
            trigger: the trigger to deactivate.
        """
        # We don't need to do anything here to change the event hub
        # configuration. The in-server event hub already uses the database
        # as the source of truth regarding configured active triggers.

    def publish_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> None:
        """Process an incoming event and trigger all configured actions.

        This will first check for any subscribers/triggers for this event,
        then log the event for later reference and finally perform the
        configured action(s).

        Args:
            event: The event.
            event_source: The event source that produced the event.
        """
        triggers = self.get_matching_active_triggers_for_event(
            event=event, event_source=event_source
        )

        for trigger in triggers:
            action_callback = self.action_handlers.get(
                (trigger.action_flavor, trigger.action_subtype)
            )
            if not action_callback:
                logger.error(
                    f"The event hub could not deliver event to action handler "
                    f"for flavor {trigger.action_flavor} and subtype "
                    f"{trigger.action_subtype} because no handler was found."
                )
                continue

            self.trigger_action(
                event=event,
                event_source=event_source,
                trigger=trigger,
                action_callback=action_callback,
            )

    def get_matching_active_triggers_for_event(
        self,
        event: BaseEvent,
        event_source: EventSourceResponse,
    ) -> List[TriggerResponse]:
        """Get all triggers that match an incoming event.

        Args:
            event: The inbound event.
            event_source: The event source which emitted the event.

        Returns:
            The list of matching triggers.
        """
        # get all event sources configured for this flavor
        triggers: List[TriggerResponse] = depaginate(
            self.zen_store.list_triggers,
            trigger_filter_model=TriggerFilter(
                project=event_source.project_id,
                event_source_id=event_source.id,
                is_active=True,
            ),
            hydrate=True,
        )

        trigger_list: List[TriggerResponse] = []

        for trigger in triggers:
            # For now, the matching of trigger filters vs event is implemented
            # in each filter class. This is not ideal and should be refactored
            # to a more generic solution that doesn't require the plugin
            # implementation to be imported here.
            try:
                plugin_flavor = plugin_flavor_registry().get_flavor_class(
                    name=event_source.flavor,
                    _type=PluginType.EVENT_SOURCE,
                    subtype=event_source.plugin_subtype,
                )
            except KeyError:
                logger.exception(
                    f"Could not find plugin flavor for event source "
                    f"{event_source.id} and flavor {event_source.flavor}. "
                    f"Skipping trigger {trigger.id}."
                )
                continue

            assert issubclass(plugin_flavor, BaseEventSourceFlavor)

            event_filter_config_class = plugin_flavor.EVENT_FILTER_CONFIG_CLASS
            try:
                event_filter = event_filter_config_class(
                    **trigger.event_filter if trigger.event_filter else {}
                )
            except ValidationError:
                logger.exception(
                    f"Could not instantiate event filter config class for "
                    f"event source {event_source.id}. Skipping trigger "
                    f"{trigger.id}."
                )
                continue

            if event_filter.event_matches_filter(event=event):
                trigger_list.append(trigger)

        logger.debug(
            f"For event {event} and event source {event_source}, "
            f"the following triggers matched: {trigger_list}"
        )

        return trigger_list


event_hub = InternalEventHub()
