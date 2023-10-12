#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Model representing schedules."""
import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import root_validator

from zenml.config.schedule import Schedule
from zenml.logger import get_logger
from zenml.new_models.base import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseMetadata,
    hydrated_property,
    update_model,
)

logger = get_logger(__name__)


# ------------------ Request Model ------------------


class ScheduleRequest(WorkspaceScopedRequest):
    """Request model for schedules."""

    name: str
    active: bool

    cron_expression: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    interval_second: Optional[datetime.timedelta] = None
    catchup: bool = False

    orchestrator_id: Optional[UUID]
    pipeline_id: Optional[UUID]

    @root_validator
    def _ensure_cron_or_periodic_schedule_configured(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensures that the cron expression or start time + interval are set.

        Args:
            values: All attributes of the schedule.

        Returns:
            All schedule attributes.

        Raises:
            ValueError: If no cron expression or start time + interval were
                provided.
        """
        cron_expression = values.get("cron_expression")
        periodic_schedule = values.get("start_time") and values.get(
            "interval_second"
        )

        if cron_expression and periodic_schedule:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "values for `start_time` and `interval_seconds`. The resulting "
                "behavior depends on the concrete orchestrator implementation "
                "but will usually ignore the interval and use the cron "
                "expression."
            )
            return values
        elif cron_expression or periodic_schedule:
            return values
        else:
            raise ValueError(
                "Either a cron expression or start time and interval seconds "
                "need to be set for a valid schedule."
            )


# ------------------ Update Model ------------------


@update_model
class ScheduleUpdate(ScheduleRequest):
    """Update model for schedules"""


# ------------------ Response Model ------------------


class ScheduleResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response model metadata for schedules."""

    orchestrator_id: Optional[UUID]
    pipeline_id: Optional[UUID]


class ScheduleResponse(Schedule, WorkspaceScopedResponse):
    """Response models for schedules."""

    # Entity fields
    name: str
    active: bool
    cron_expression: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    interval_second: Optional[datetime.timedelta] = None
    catchup: bool = False

    # Metadata related field, method and properties
    metadata: Optional["ScheduleResponseMetadata"]

    def get_hydrated_version(self) -> "ScheduleResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_schedule(self.id)

    @hydrated_property
    def orchestrator_id(self):
        """The orchestrator_id property."""
        return self.metadata.orchestrator_id

    @hydrated_property
    def pipeline_id(self):
        """The pipeline_id property."""
        return self.metadata.pipeline_id

    # Helper methods
    @property
    def utc_start_time(self) -> Optional[str]:
        """Optional ISO-formatted string of the UTC start time.

        Returns:
            Optional ISO-formatted string of the UTC start time.
        """
        if not self.start_time:
            return None

        return self.start_time.astimezone(datetime.timezone.utc).isoformat()

    @property
    def utc_end_time(self) -> Optional[str]:
        """Optional ISO-formatted string of the UTC end time.

        Returns:
            Optional ISO-formatted string of the UTC end time.
        """
        if not self.end_time:
            return None

        return self.end_time.astimezone(datetime.timezone.utc).isoformat()
