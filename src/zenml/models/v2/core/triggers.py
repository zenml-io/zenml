#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Models representing triggers."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ScheduleEngine, TriggerCategory, TriggerType
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
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = logging.getLogger(__name__)


# ------------------ Request Model ------------------


class SchedulePayload(BaseModel):
    """Class representing a schedule parameters."""

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
    engine: ScheduleEngine = ScheduleEngine.native

    @field_validator(
        "start_time", "end_time", "run_once_start_time", mode="after"
    )
    @classmethod
    def _ensure_tzunaware_utc(cls, value: datetime | None) -> datetime | None:
        """Ensures that all datetimes are timezone unaware and in UTC time.

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
    def _ensure_cron_or_periodic_schedule_configured(
        self,
    ) -> "SchedulePayload":
        """Ensures that the cron expression or start time + interval are set.

        Returns:
            All schedule attributes.

        Raises:
            ValueError: If no cron expression or start time + interval were
                provided.
        """
        cron_expression = self.cron_expression
        periodic_schedule = self.start_time and self.interval
        run_once_starts_at = self.run_once_start_time

        if cron_expression and periodic_schedule:
            logger.warning(
                "This schedule was created with a cron expression as well as "
                "values for `start_time` and `interval`. The resulting "
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
                "Either a cron expression, a start time and interval "
                "or a run once start time "
                "need to be set for a valid schedule."
            )

    @model_validator(mode="after")
    def _correct_time_boundaries(self) -> "SchedulePayload":
        if not (self.end_time and self.start_time):
            return self

        if self.end_time <= self.start_time:
            raise ValueError("The end time must be after the start time.")

        return self


class TriggerRequest(ProjectScopedRequest):
    """Request model for triggers."""

    name: str
    active: bool = Field(
        default=True,
        description="Whether to activate this trigger upon creation.",
    )
    description: str | None = None
    trigger_type: TriggerType
    category: TriggerCategory
    data: SchedulePayload


# ------------------ Update Model ------------------


class ScheduleUpdatePayload(BaseUpdate):
    """Update model for schedule triggers."""

    cron_expression: str | None = None
    interval: int | None = None
    next_occurrence: datetime | None = None
    start_time: datetime | None = None

    @model_validator(mode="after")
    def check_mutual_exclusive_options(self) -> "ScheduleUpdatePayload":
        """Validates that mutual exclusive options are not both provided.

        Returns:
            The instance of the ScheduleUpdatePayload.

        Raises:
            ValueError: If mutual exclusive options are provided.
        """
        if self.interval is not None and self.next_occurrence is not None:
            raise ValueError(
                "The interval and next_occurrence schedule options are mutually exclusive. "
            )

        return self


class TriggerUpdate(BaseUpdate):
    """Update model for triggers."""

    name: str | None = None
    active: bool | None = None
    data: ScheduleUpdatePayload | None = None


# ------------------ Response Model ------------------


class ScheduleResponsePayload(SchedulePayload):
    """Response model for schedules."""

    next_occurrence: datetime | None = None


class TriggerResponseBody(ProjectScopedResponseBody):
    """Response body for triggers."""

    active: bool = Field(
        default=True,
        description="Whether to activate this trigger upon creation.",
    )
    trigger_type: TriggerType
    category: TriggerCategory
    data: ScheduleResponsePayload | None
    is_archived: bool


class TriggerResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for triggers."""

    pass


class TriggerResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the trigger entity."""

    snapshots: Optional[list["PipelineSnapshotResponse"]] = None
    user: Optional["UserResponse"] = None


class TriggerResponse(
    ProjectScopedResponse[
        TriggerResponseBody,
        TriggerResponseMetadata,
        TriggerResponseResources,
    ],
):
    """Response model for schedules."""

    name: str = Field(
        title="Name of this trigger.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "TriggerResponse":
        """Get the hydrated version of this schedule.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_trigger(self.id)

    # Body and metadata properties
    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def is_archived(self) -> bool:
        """The `is_archived` property.

        Returns:
            the value of the property.
        """
        return self.get_body().is_archived

    @property
    def trigger_type(self) -> TriggerType:
        """The `trigger_type` property.

        Returns:
            The value of the property.
        """
        return self.get_body().trigger_type

    @property
    def schedule(self) -> ScheduleResponsePayload:
        """The 'schedule` property.

        Returns:
            The schedule object data

        Raises:
            ValueError: If not a trigger of schedule type.
        """
        if self.trigger_type == TriggerType.schedule:
            return self.get_body().data  # type: ignore[return-value]

        raise ValueError(
            f"Trigger of type {self.trigger_type} does not have schedule data."
        )

    @property
    def data(self) -> ScheduleResponsePayload | None:
        """The 'data' property.

        It would be best to avoid using this property and opt to use properties
        with specific return types like 'schedule'

        Returns:
            The trigger dynamic data.
        """
        return self.get_body().data

    @property
    def snapshots(self) -> list["PipelineSnapshotResponse"]:
        """Implements he 'snapshots' property.

        Returns:
            A list of associated snapshots.
        """
        return self.get_resources().snapshots or []


# ------------------ Filter Model ------------------


class TriggerFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of all Users."""

    FILTER_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "next_occurrence_upper_bound",
    ]

    active: bool | None = Field(
        default=None,
        description="If the schedule is active",
    )
    name: str | None = Field(
        default=None,
        description="Name of the schedule",
    )
    is_archived: bool = Field(
        default=False,
        description="Whether or not the schedule is archived",
    )
    trigger_type: TriggerType


def apply_schedule_update(
    update: ScheduleUpdatePayload,
    current: ScheduleResponsePayload,
    re_activated: bool,
) -> ScheduleResponsePayload:
    """Apply schedule update to a current schedule.

    Validates transition state, resets state on frequency option transition,
    re-calculates next occurrence if necessary.

    Args:
        update: A ScheduleUpdatePayload object.
        current: A ScheduleResponsePayload object.
        re_activated: Whether the schedule is being re-activated.

    Returns:
        The updated ScheduleResponsePayload object.

    Raises:
        ValueError:
    """
    from zenml.utils.native_schedules import calculate_first_occurrence

    data = current.model_dump()

    need_to_recalculate_next_occurrence = re_activated

    if update.start_time:
        need_to_recalculate_next_occurrence = True
        data["start_time"] = update.start_time

    if update.interval:
        need_to_recalculate_next_occurrence = True
        data["interval"] = update.interval

        if data[
            "cron_expression"
        ]:  # If we switch option, we should clean-up previous values
            data["cron_expression"] = None
        if data["run_once_start_time"]:
            data["run_once_start_time"] = None
        if not data["start_time"]:
            raise ValueError("To set interval, you must specify a start time.")

    if update.cron_expression:
        need_to_recalculate_next_occurrence = True
        data["cron_expression"] = update.cron_expression

        if data[
            "interval"
        ]:  # If we switch option, we should clean-up previous values
            data["interval"] = None
        if data["run_once_start_time"]:
            data["run_once_start_time"] = None

    response = ScheduleResponsePayload(**data)

    if need_to_recalculate_next_occurrence:
        response.next_occurrence = calculate_first_occurrence(
            schedule=response
        )

    return response
