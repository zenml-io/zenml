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
"""Models representing schedules."""

import datetime
from typing import Optional, Union
from uuid import UUID

from pydantic import Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.logger import get_logger
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
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
    run_once_start_time: Optional[datetime.datetime] = None

    orchestrator_id: Optional[UUID]
    pipeline_id: Optional[UUID]

    @model_validator(mode="after")
    def _ensure_cron_or_periodic_schedule_configured(
        self,
    ) -> "ScheduleRequest":
        """Ensures that the cron expression or start time + interval are set.

        Returns:
            All schedule attributes.

        Raises:
            ValueError: If no cron expression or start time + interval were
                provided.
        """
        cron_expression = self.cron_expression
        periodic_schedule = self.start_time and self.interval_second
        run_once_starts_at = self.run_once_start_time

        if cron_expression and periodic_schedule:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "values for `start_time` and `interval_seconds`. The resulting "
                "behavior depends on the concrete orchestrator implementation "
                "but will usually ignore the interval and use the cron "
                "expression."
            )
            return self
        elif cron_expression and run_once_starts_at:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "a value for `run_once_start_time`. The resulting behavior "
                "depends on the concrete orchestrator implementation but will "
                "usually ignore the `run_once_start_time`."
            )
            return self
        elif cron_expression or periodic_schedule or run_once_starts_at:
            return self
        else:
            raise ValueError(
                "Either a cron expression, a start time and interval seconds "
                "or a run once start time "
                "need to be set for a valid schedule."
            )


# ------------------ Update Model ------------------


class ScheduleUpdate(BaseUpdate):
    """Update model for schedules."""

    name: Optional[str] = None
    active: Optional[bool] = None
    cron_expression: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    interval_second: Optional[datetime.timedelta] = None
    catchup: Optional[bool] = None
    run_once_start_time: Optional[datetime.datetime] = None
    orchestrator_id: Optional[UUID] = None
    pipeline_id: Optional[UUID] = None


# ------------------ Response Model ------------------


class ScheduleResponseBody(WorkspaceScopedResponseBody):
    """Response body for schedules."""

    active: bool
    cron_expression: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    interval_second: Optional[datetime.timedelta] = None
    catchup: bool = False
    run_once_start_time: Optional[datetime.datetime] = None


class ScheduleResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for schedules."""

    orchestrator_id: Optional[UUID]
    pipeline_id: Optional[UUID]


class ScheduleResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the schedule entity."""


class ScheduleResponse(
    WorkspaceScopedResponse[
        ScheduleResponseBody,
        ScheduleResponseMetadata,
        ScheduleResponseResources,
    ],
):
    """Response model for schedules."""

    name: str = Field(
        title="Name of this schedule.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "ScheduleResponse":
        """Get the hydrated version of this schedule.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_schedule(self.id)

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

    # Body and metadata properties
    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def cron_expression(self) -> Optional[str]:
        """The `cron_expression` property.

        Returns:
            the value of the property.
        """
        return self.get_body().cron_expression

    @property
    def start_time(self) -> Optional[datetime.datetime]:
        """The `start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().start_time

    @property
    def end_time(self) -> Optional[datetime.datetime]:
        """The `end_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().end_time

    @property
    def run_once_start_time(self) -> Optional[datetime.datetime]:
        """The `run_once_start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().run_once_start_time

    @property
    def interval_second(self) -> Optional[datetime.timedelta]:
        """The `interval_second` property.

        Returns:
            the value of the property.
        """
        return self.get_body().interval_second

    @property
    def catchup(self) -> bool:
        """The `catchup` property.

        Returns:
            the value of the property.
        """
        return self.get_body().catchup

    @property
    def orchestrator_id(self) -> Optional[UUID]:
        """The `orchestrator_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().orchestrator_id

    @property
    def pipeline_id(self) -> Optional[UUID]:
        """The `pipeline_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_id


# ------------------ Filter Model ------------------


class ScheduleFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Users."""

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace scope of the schedule.",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that created the schedule",
        union_mode="left_to_right",
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline that the schedule is attached to.",
        union_mode="left_to_right",
    )
    orchestrator_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Orchestrator that the schedule is attached to.",
        union_mode="left_to_right",
    )
    active: Optional[bool] = Field(
        default=None,
        description="If the schedule is active",
    )
    cron_expression: Optional[str] = Field(
        default=None,
        description="The cron expression, describing the schedule",
    )
    start_time: Optional[Union[datetime.datetime, str]] = Field(
        default=None, description="Start time", union_mode="left_to_right"
    )
    end_time: Optional[Union[datetime.datetime, str]] = Field(
        default=None, description="End time", union_mode="left_to_right"
    )
    interval_second: Optional[Optional[float]] = Field(
        default=None,
        description="The repetition interval in seconds",
    )
    catchup: Optional[bool] = Field(
        default=None,
        description="Whether or not the schedule is set to catchup past missed "
        "events",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the schedule",
    )
    run_once_start_time: Optional[Union[datetime.datetime, str]] = Field(
        default=None,
        description="The time at which the schedule should run once",
        union_mode="left_to_right",
    )
