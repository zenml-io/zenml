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
"""Internal scheduler event source flavor definition."""
from typing import ClassVar, Type

from zenml.event_sources.schedules.base_schedule_event_plugin import (
    BaseScheduleEventSourcePluginFlavor,
)
from zenml.scheduler.scheduler_event_source import (
    SchedulerEventFilterConfiguration,
    SchedulerEventSourceConfiguration,
    SchedulerEventSourcePlugin,
)

INTERNAL_SCHEDULER_EVENT_FLAVOR = "internal_scheduler"


class SchedulerEventSourceFlavor(BaseScheduleEventSourcePluginFlavor):
    """Enables users to configure scheduled events."""

    FLAVOR: ClassVar[str] = INTERNAL_SCHEDULER_EVENT_FLAVOR
    PLUGIN_CLASS: ClassVar[
        Type[SchedulerEventSourcePlugin]
    ] = SchedulerEventSourcePlugin

    # EventPlugin specific
    EVENT_SOURCE_CONFIG_CLASS: ClassVar[
        Type[SchedulerEventSourceConfiguration]
    ] = SchedulerEventSourceConfiguration
    EVENT_FILTER_CONFIG_CLASS: ClassVar[
        Type[SchedulerEventFilterConfiguration]
    ] = SchedulerEventFilterConfiguration
