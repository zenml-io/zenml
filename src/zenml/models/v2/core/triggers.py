# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Base classes for Trigger implementations."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import TriggerFlavor, TriggerType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models import PipelineSnapshotResponse, UserResponse


class TriggerBase(BaseModel, ABC):
    """Base class for triggers."""

    name: str = Field(
        max_length=STR_FIELD_MAX_LENGTH,
        description="The name of the trigger.",
    )
    active: bool
    type: TriggerType


class TriggerRequest(ProjectScopedRequest, TriggerBase, ABC):
    """Base class for trigger requests."""

    flavor: TriggerFlavor

    @abstractmethod
    def get_config(self) -> str:
        """Calculates a serialized JSON object for the type-specific fields of the trigger.

        Returns:
            A JSON string representing the trigger-type configuration.
        """
        pass

    @abstractmethod
    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates extra, type-specific fields needed for the trigger.

        Returns:
            A dictionary of extra fields (e.g. {"next_occurrence": "..."}
        """
        pass


class TriggerUpdate(TriggerBase, BaseUpdate, ABC):
    """Base trigger update class."""

    @abstractmethod
    def get_config(self) -> str:
        """Calculates a serialized JSON object for the type-specific fields of the trigger.

        Returns:
            A JSON string representing the trigger-type configuration.
        """
        pass

    @abstractmethod
    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates extra, type-specific fields needed for the trigger.

        Returns:
            A dictionary of extra fields (e.g. {"next_occurrence": "..."}) to be stored in the database.
            IMPORTANT: These fields must match the attributes defined in the `TriggerSchema` ORM class.
        """
        pass


class TriggerResponseBody(ProjectScopedResponseBody, TriggerBase, ABC):
    """Response body for triggers."""

    is_archived: bool
    flavor: TriggerFlavor

    @abstractmethod
    def get_extra_fields(self) -> list[str]:
        """Specify the extra fields needed for the trigger.

        Returns:
            A list of extra fields (e.g. ["next_occurrence"]).
        """
        pass


class TriggerResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for triggers."""

    pass


class TriggerResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the schedule entity."""

    snapshots: Optional[list["PipelineSnapshotResponse"]] = None
    user: Optional["UserResponse"] = None


class TriggerFilter(ProjectScopedFilter):
    """Base class for filtering triggers."""

    name: str | None = Field(
        default=None,
        description="The name of the trigger.",
    )
    active: bool | None = Field(
        default=None,
        description="Whether the trigger should be active.",
    )
    is_archived: bool = Field(
        default=False,
        description="Whether the trigger should be archived.",
    )
    flavor: TriggerFlavor | None = Field(
        default=None,
        description="The trigger flavor.",
    )
    type: TriggerType | None = Field(
        default=None,
        description="The trigger type.",
    )
    next_occurrence: datetime | str | None = Field(
        default=None,
        description="The next occurrence of the trigger (applicable only for schedules).",
        union_mode="left_to_right",
    )


class ScheduleTrigger(BaseModel):
    """Base class for schedule-specific parameters."""

    cron_expression: str | None = None
    interval: int | None = Field(
        default=None,
        ge=60,
        description="Scheduling option: Execute on intervals of N seconds after start time.",
    )
    end_time: datetime | None = None
    start_time: datetime | None = None
    run_once_start_time: datetime | None = Field(
        default=None,
        description="Scheduling option: Execute once on selected start time.",
    )

    @field_validator(
        "start_time", "end_time", "run_once_start_time", mode="after"
    )
    @classmethod
    def _tz_unaware_utc(cls, value: datetime | None) -> datetime | None:
        """Ensures that all datetime objects are timezone unaware and in UTC time.

        Args:
            value: The datetime.

        Returns:
            The datetime in UTC time without timezone.
        """
        if value and value.tzinfo:
            value = value.astimezone(timezone.utc)
            value = value.replace(tzinfo=None)

        return value

    @model_validator(mode="after")
    def _interval_combined_with_start(self) -> "ScheduleTrigger":
        """Ensures interval is combined with start time.

        Returns:
            The ScheduleTrigger instance.

        Raises:
            ValueError: If interval is set without a start time.
        """
        if self.interval is not None and self.start_time is None:
            raise ValueError("Interval must be set with start time.")

        return self

    @model_validator(mode="after")
    def _unique_scheduling_option(
        self,
    ) -> "ScheduleTrigger":
        """Ensures exactly one frequency configuration option is provided.

        Returns:
            The ScheduleTrigger instance.

        Raises:
            ValueError: If zero or more than one frequency options are provided.
        """
        num_of_set_options = sum(
            1 if option is not None else 0
            for option in [
                self.cron_expression,
                self.interval,
                self.run_once_start_time,
            ]
        )

        if num_of_set_options == 0:
            raise ValueError(
                "You must specify an execution option (cron, interval, one-off) for the schedule."
            )
        if num_of_set_options > 1:
            raise ValueError(
                "You must specify exactly one option (cron, interval, one-off) for the schedule."
            )

        return self

    @model_validator(mode="after")
    def _correct_time_boundaries(self) -> "ScheduleTrigger":
        """Ensure start and end times set valid boundaries.

        Returns:
            The ScheduleTrigger instance.

        Raises:
            ValueError: If start time is greater than end time.
        """
        if not (self.end_time and self.start_time):
            return self

        if self.end_time <= self.start_time:
            raise ValueError("The end time must be after the start time.")

        return self


class ScheduleTriggerRequest(TriggerRequest, ScheduleTrigger):
    """Class representing a ScheduleTrigger request."""

    def get_config(self) -> str:
        """Returns the serialized blob of custom trigger fields.

        Returns:
            Json-dump of ScheduleTrigger config.
        """
        return self.model_dump_json(
            include=set(ScheduleTrigger.model_fields),
        )

    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates and returns extra flat fields.

        Returns:
            A dictionary with extra fields (next occurrence or empty).
        """
        if self.flavor == TriggerFlavor.NATIVE_SCHEDULE:
            from zenml.utils.native_schedules import calculate_first_occurrence

            return {
                "next_occurrence": calculate_first_occurrence(
                    cron_expression=self.cron_expression,
                    start_time=self.start_time,
                    interval=self.interval,
                    run_once_start_time=self.run_once_start_time,
                )
            }
        return {}


class ScheduleTriggerUpdate(TriggerUpdate, ScheduleTrigger):
    """Class representing a ScheduleTrigger update."""

    type: Literal[TriggerType.SCHEDULE] = TriggerType.SCHEDULE
    flavor: Literal[TriggerFlavor.NATIVE_SCHEDULE] = (
        TriggerFlavor.NATIVE_SCHEDULE
    )
    next_occurrence: datetime | None = None

    def get_config(self) -> str:
        """Returns the serialized blob of custom trigger fields.

        Returns:
            Json-dump of ScheduleTrigger config.
        """
        return self.model_dump_json(include=set(ScheduleTrigger.model_fields))

    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates and returns extra flat fields.

        Returns:
            A dictionary with extra fields (next occurrence or empty).
        """
        occurrence_altering_values = [
            self.start_time,
            self.cron_expression,
            self.interval,
        ]

        if not self.flavor == TriggerFlavor.NATIVE_SCHEDULE:
            return {}

        if self.next_occurrence is not None:
            return {
                "next_occurrence": self.next_occurrence,
            }

        if any(field is not None for field in occurrence_altering_values):
            from zenml.utils.native_schedules import calculate_first_occurrence

            return {
                "next_occurrence": calculate_first_occurrence(
                    cron_expression=self.cron_expression,
                    start_time=self.start_time,
                    interval=self.interval,
                    run_once_start_time=self.run_once_start_time,
                )
            }

        return {}


class ScheduleTriggerResponseBody(ScheduleTrigger, TriggerResponseBody):
    """Class representing a ScheduleTrigger response body."""

    next_occurrence: datetime | None = None

    def get_extra_fields(self) -> list[str]:
        """Returns the extra fields (e.g. next occurrence).

        Returns:
            The extra fields for the schedule payload.
        """
        return ["next_occurrence"]


class ScheduleTriggerResponse(
    ProjectScopedResponse[
        ScheduleTriggerResponseBody,
        TriggerResponseMetadata,
        TriggerResponseResources,
    ]
):
    """Class representing a ScheduleTrigger response."""

    @property
    def is_archived(self) -> bool:
        """Implements the 'is_archived' property.

        Returns:
            True if the trigger is archived.
        """
        return self.get_body().is_archived

    @property
    def active(self) -> bool:
        """Implements the 'is_active' property.

        Returns:
            True if the trigger is active.
        """
        return self.get_body().active

    @property
    def name(self) -> str:
        """Implements the 'name' property.

        Returns:
            The trigger name.
        """
        return self.get_body().name

    @property
    def type(self) -> TriggerType:
        """Implements the 'type' property.

        Returns:
            The trigger type.
        """
        return self.get_body().type

    @property
    def flavor(self) -> TriggerFlavor:
        """Implements the 'flavor' property.

        Returns:
            The trigger flavor.
        """
        return self.get_body().flavor

    @property
    def next_occurrence(self) -> datetime | None:
        """Implements the 'next_occurrence' property.

        Returns:
            The schedule's next occurrence.
        """
        return self.get_body().next_occurrence

    @property
    def cron_expression(self) -> str | None:
        """Implements the 'cron_expression' property.

        Returns:
            The schedule's cron expression.
        """
        return self.get_body().cron_expression

    @property
    def start_time(self) -> datetime | None:
        """Implements the 'start_time' property.

        Returns:
            The schedule's start time.
        """
        return self.get_body().start_time

    @property
    def interval(self) -> int | None:
        """Implements the 'interval' property.

        Returns:
            The schedule's interval.
        """
        return self.get_body().interval

    @property
    def end_time(self) -> datetime | None:
        """Implements the 'end_time' property.

        Returns:
            The schedule's end time.
        """
        return self.get_body().end_time

    @property
    def run_once_start_time(self) -> datetime | None:
        """Implements the 'run_once_start_time' property.

        Returns:
            The schedule's run once start time.
        """
        return self.get_body().run_once_start_time

    @property
    def snapshots(self) -> list["PipelineSnapshotResponse"] | None:
        """Implements the 'snapshots' property.

        Returns:
            A list of snapshots the triggers is attached to.
        """
        return self.get_resources().snapshots
