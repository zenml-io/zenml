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
"""Implementation of the internal scheduler event source plugin."""
from typing import Type

from zenml.event_sources.base_event_source import BaseEvent
from zenml.event_sources.schedules.base_schedule_event import (
    BaseScheduleEvent,
    BaseScheduleEventSource,
    ScheduleEventFilterConfig,
    ScheduleEventSourceConfig,
)
from zenml.logger import get_logger
from zenml.models import EventSourceRequest, EventSourceResponse

logger = get_logger(__name__)


class ScheduleEvent(BaseScheduleEvent):
    """Schedule event."""


class SchedulerEventFilterConfiguration(ScheduleEventFilterConfig):
    """Configuration for scheduler event filters."""

    cron_expression: str

    def event_matches_filter(self, event: BaseEvent) -> bool:
        """Checks the filter against the inbound event."""
        return True


class SchedulerEventSourceConfiguration(ScheduleEventSourceConfig):
    """Configuration for scheduler source filters."""


class SchedulerEventSourcePlugin(BaseScheduleEventSource):
    """Handler for all github events."""

    @property
    def config_class(self) -> Type[ScheduleEventSourceConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return SchedulerEventSourceConfiguration

    def _create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Wraps the zen_store creation method to add plugin specific functionality."""
        # Implementations will be able to actually configure an external CronJobs
        #  before storing them in the database
        created_event_source = self.zen_store.create_event_source(
            event_source=event_source
        )
        return created_event_source
