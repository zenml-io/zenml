#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from typing import Any, Dict

from zenml.enums import PluginSubType, PluginType
from zenml.event_sources.base_event_source_plugin import BaseEventSourcePlugin
from zenml.plugins.plugin_flavor_registry import logger, plugin_flavor_registry


class EventHub:
    """Handler for all events."""

    def process_event(
        self,
        incoming_event: Dict[str, Any],
        flavor: str,
        event_source_subtype: PluginSubType,
    ):
        """Process an incoming event and execute all configured actions.

        This will first check for any subscribers/triggers for this event,
        then log the event for later reference and finally perform the
        configured action(s).

        Args:
            incoming_event: Generic event
            flavor: Flavor of Event
            event_source_subtype: Subtype of Event

        """
        try:
            plugin_cls = plugin_flavor_registry.get_plugin_implementation(
                flavor=flavor,
                _type=PluginType.EVENT_SOURCE,
                subtype=event_source_subtype,
            )
            # # Store event for future reference
        # Get all actions to be executed
        except KeyError as e:
            # TODO: raise the appropriate exception
            logger.exception(e)
            raise KeyError(e)
        else:
            assert isinstance(plugin_cls, BaseEventSourcePlugin)
            triggers = plugin_cls.get_matching_triggers_for_event(
                incoming_event
            )
        # TODO: Store event for future reference
        # TODO: Create a trigger execution linked to the event and the trigger
        logger.debug(triggers)


event_hub = EventHub()
