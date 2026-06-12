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
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Dict,
    Generic,
    Literal,
    Optional,
    Type,
    TypeAlias,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import (
    PLATFORM_EVENT_REGISTRY,
    SourceType,
    TriggerFlavor,
    TriggerRunConcurrency,
    TriggerType,
)
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.filter import (
    AnyQuery,
    BaseFilter,
    DatetimeFilterOption,
    EnumFilterOption,
    StringFilterOption,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.time_utils import utc_now

# ----------- DISPATCH STATE MODELS ------------------ #


class TriggerDispatchStatusCode(StrEnum):
    """User-facing dispatch status values for trigger-snapshot execution."""

    SUCCESS = "SUCCESS"
    SKIPPED_CONCURRENCY = "SKIPPED_CONCURRENCY"
    SKIPPED_MAX_RUNS = "SKIPPED_MAX_RUNS"
    ERROR = "ERROR"


class TriggerDispatchErrorSeverity(StrEnum):
    """Severity levels for trigger dispatch errors."""

    MINOR = "Minor"
    MAJOR = "Major"
    CRITICAL = "Critical"


class TriggerSnapshotDispatchState(BaseModel):
    """User-facing trigger dispatch state stored on trigger-snapshot links.

    Persisted only for paths where a concrete ``(trigger_id, snapshot_id)``
    association row exists; unattributable exits stay in structured logs.
    """

    MESSAGE_MAX_LENGTH: ClassVar[int] = 4096
    ERROR_TYPE_MAX_LENGTH: ClassVar[int] = 255
    STACK_TRACE_MAX_LENGTH: ClassVar[int] = 16_384

    last_status: TriggerDispatchStatusCode
    last_status_at: datetime | None = Field(
        default=None,
        description="Timestamp of the latest recorded status transition.",
    )
    last_error_message: str | None = Field(
        default=None,
        max_length=MESSAGE_MAX_LENGTH,
        description=(
            "Friendly user-facing message describing the latest error."
        ),
    )
    last_error_type: str | None = Field(
        default=None,
        max_length=ERROR_TYPE_MAX_LENGTH,
        description="Implementation-level error classifier.",
    )
    last_error_severity: TriggerDispatchErrorSeverity | None = Field(
        default=None,
        description="Severity level of the latest error.",
    )
    last_error_stack_trace: str | None = Field(
        default=None,
        max_length=STACK_TRACE_MAX_LENGTH,
        description="Stack trace accompanying the last error",
    )
    last_error_at: datetime | None = Field(
        default=None,
        description=(
            "Timestamp of the last error in the current consecutive error-type "
            "streak."
        ),
    )
    first_error_at: datetime | None = Field(
        default=None,
        description=(
            "Timestamp of the first error in the current consecutive "
            "error-type streak."
        ),
    )
    last_error_count: int = Field(
        default=0,
        ge=0,
        description="Number of times the latest error type occurred consecutively.",
    )

    @field_validator("last_error_message", mode="before")
    @classmethod
    def _truncate_message(cls, value: Any) -> Any:
        """Truncate message payloads to storage-safe length.

        Args:
            value: Incoming message value.

        Returns:
            Possibly truncated message value.
        """
        if isinstance(value, str):
            return value[: cls.MESSAGE_MAX_LENGTH]
        return value

    @field_validator("last_error_stack_trace", mode="before")
    @classmethod
    def _truncate_stack_trace_tail(cls, value: Any) -> Any:
        """Trim stack traces to keep the most relevant bottom entries.

        Args:
            value: Incoming stack trace.

        Returns:
            Possibly tail-trimmed stack trace.
        """
        if isinstance(value, str):
            return value[-cls.STACK_TRACE_MAX_LENGTH :]
        return value

    @model_validator(mode="after")
    def _set_error_defaults(self) -> "TriggerSnapshotDispatchState":
        """Initialize default error metadata for freshly created errors.

        Returns:
            The validated state.
        """
        if self.last_status_at is None:
            self.last_status_at = utc_now()
        if self.last_status == TriggerDispatchStatusCode.ERROR:
            if self.last_error_count == 0:
                self.last_error_count = 1
            if self.last_error_at is None:
                self.last_error_at = utc_now()
            if self.first_error_at is None:
                self.first_error_at = self.last_error_at
        return self

    def apply_new_state(
        self,
        new_state: "TriggerSnapshotDispatchState",
    ) -> None:
        """Apply a new dispatch state on top of this persisted state.

        Args:
            new_state: Newly reported dispatch state.
        """
        if new_state.last_status == TriggerDispatchStatusCode.ERROR:
            if (
                self.last_status == TriggerDispatchStatusCode.ERROR
                and self.last_error_type == new_state.last_error_type
            ):
                self.last_error_count += 1
                if self.first_error_at is None:
                    self.first_error_at = (
                        self.last_error_at
                        or new_state.first_error_at
                        or new_state.last_error_at
                        or utc_now()
                    )
            else:
                self.last_error_count = 1
                self.first_error_at = (
                    new_state.first_error_at
                    or new_state.last_error_at
                    or utc_now()
                )
            self.last_error_message = new_state.last_error_message
            self.last_error_type = new_state.last_error_type
            self.last_error_severity = new_state.last_error_severity
            self.last_error_stack_trace = new_state.last_error_stack_trace
            self.last_error_at = new_state.last_error_at or utc_now()

        self.last_status = new_state.last_status
        self.last_status_at = new_state.last_status_at or utc_now()

    def clear_error_details(self) -> None:
        """Clear stored error details while keeping the last status."""
        self.last_error_message = None
        self.last_error_type = None
        self.last_error_severity = None
        self.last_error_stack_trace = None
        self.last_error_at = None
        self.first_error_at = None
        self.last_error_count = 0


if TYPE_CHECKING:
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
        UserResponse,
    )
    from zenml.models.v2.base.filter import AnySchema


# ----------- TRIGGER BASE CLASSES ------------------- #


class TriggerBase(BaseModel, ABC):
    """Base class for triggers."""

    name: str = Field(
        max_length=STR_FIELD_MAX_LENGTH,
        description="The name of the trigger.",
    )
    active: bool = Field(
        default=True,
        description="Whether the trigger should be active.",
    )
    type: TriggerType
    concurrency: TriggerRunConcurrency = Field(
        default=TriggerRunConcurrency.SKIP,
        description="How to handle concurrently running triggers "
        "(pipeline runs generated from the same trigger & snapshot).",
    )


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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Get the analytics metadata for the model.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["type"] = self.type.value
        metadata["flavor"] = self.flavor.value
        return metadata


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

    snapshots: list["PipelineSnapshotResponse"] = []
    executable_snapshots: list["PipelineSnapshotResponse"] = []
    user: Optional["UserResponse"] = None
    latest_run: Optional["PipelineRunResponse"] = None
    snapshot_dispatch_states: dict[UUID, TriggerSnapshotDispatchState] = Field(
        default_factory=dict
    )


class UnScopedTriggerFilter(BaseFilter):
    """Base class for filtering triggers."""

    FILTER_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "is_archived",
        "type",
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[list[str]] = [
        *BaseFilter.API_SINGLE_INPUT_PARAMS,
        "is_archived",
        "active",
    ]

    name: StringFilterOption = Field(
        default=None,
        description="The name of the trigger.",
    )
    active: bool | None = Field(
        default=None,
        description="Whether the trigger should be active.",
    )
    is_archived: bool = Field(
        default=False,
        description=(
            "Restrict results to archived or non-archived triggers. Applied as "
            "a global scope filter independently of logical_operator."
        ),
    )
    flavor: EnumFilterOption[TriggerFlavor] = Field(
        default=None,
        description="The trigger flavor.",
        union_mode="left_to_right",
    )
    type: EnumFilterOption[TriggerType] = Field(
        default=None,
        description="The trigger type.",
        union_mode="left_to_right",
    )
    next_occurrence: DatetimeFilterOption = Field(
        default=None,
        description="The next occurrence of the trigger (applicable only for schedules).",
        union_mode="left_to_right",
    )
    concurrency: EnumFilterOption[TriggerRunConcurrency] = Field(
        default=None, description="The trigger concurrency."
    )

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        from sqlmodel import col

        from zenml.zen_stores.schemas import TriggerSchema

        query = super().apply_filter(query=query, table=table)
        query = query.where(TriggerSchema.is_archived == self.is_archived)

        if self.type is not None:
            type_checks = (
                self.type if isinstance(self.type, list) else [self.type]
            )
            query = query.where(col(TriggerSchema.type).in_(type_checks))

        return query


class TriggerFilter(UnScopedTriggerFilter, ProjectScopedFilter):
    """Public class for filtering triggers."""

    FILTER_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *UnScopedTriggerFilter.FILTER_EXCLUDE_FIELDS,
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_id",
        "snapshot_id",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *UnScopedTriggerFilter.CLI_EXCLUDE_FIELDS,
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        "type",
        "flavor",
        "next_occurrence",
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[list[str]] = [
        *UnScopedTriggerFilter.API_SINGLE_INPUT_PARAMS,
        *ProjectScopedFilter.API_SINGLE_INPUT_PARAMS,
    ]

    pipeline_id: StringFilterOption = Field(
        default=None,
        description="Filter triggers by pipeline ID (triggers that are attached to this pipeline's snapshots)",
    )
    snapshot_id: StringFilterOption = Field(
        default=None,
        description="Filter triggers by snapshot ID (triggers that are attached to this snapshot)",
    )

    @property
    def filter_by_snapshot(self) -> bool:
        """Implements the `filter_by_snapshot` property.

        Returns:
            True if filtering requires snapshot fields else False.
        """
        return any(f is not None for f in [self.pipeline_id, self.snapshot_id])

    def apply_filter(
        self, query: AnyQuery, table: Type["AnySchema"]
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        from sqlmodel import col

        from zenml.zen_stores.schemas import (
            PipelineSnapshotSchema,
            TriggerSchema,
            TriggerSnapshotSchema,
        )

        query = super().apply_filter(query, table)

        if self.filter_by_snapshot:
            query = query.join(
                TriggerSnapshotSchema,
                TriggerSchema.id == TriggerSnapshotSchema.trigger_id,
            ).join(
                PipelineSnapshotSchema,
                TriggerSnapshotSchema.snapshot_id == PipelineSnapshotSchema.id,
            )

            if self.pipeline_id is not None:
                pipeline_ids = (
                    self.pipeline_id
                    if isinstance(self.pipeline_id, list)
                    else [self.pipeline_id]
                )
                query = query.where(
                    col(PipelineSnapshotSchema.pipeline_id).in_(pipeline_ids)
                )

            if self.snapshot_id is not None:
                snapshot_ids = (
                    self.snapshot_id
                    if isinstance(self.snapshot_id, list)
                    else [self.snapshot_id]
                )
                query = query.where(
                    col(TriggerSnapshotSchema.snapshot_id).in_(snapshot_ids)
                )

        return query


# ----------- SCHEDULE CLASSES ------------------- #


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
    max_runs: int | None = Field(
        default=None,
        description="Maximum number of runs to execute with this schedule.",
        ge=1,
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

    type: Literal[TriggerType.SCHEDULE] = TriggerType.SCHEDULE
    flavor: Literal[TriggerFlavor.NATIVE_SCHEDULE] = (
        TriggerFlavor.NATIVE_SCHEDULE
    )

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

    @model_validator(mode="after")
    def _next_occurrence_for_inactive(self) -> "ScheduleTriggerResponseBody":
        if not (self.active and not self.is_archived):
            self.next_occurrence = None

        return self

    def get_extra_fields(self) -> list[str]:
        """Returns the extra fields (e.g. next occurrence).

        Returns:
            The extra fields for the schedule payload.
        """
        return ["next_occurrence"]


TriggerBodyT = TypeVar("TriggerBodyT", bound="TriggerResponseBody")


class TriggerResponse(
    ProjectScopedResponse[
        TriggerBodyT,
        TriggerResponseMetadata,
        TriggerResponseResources,
    ],
    Generic[TriggerBodyT],
):
    """Class representing a base TriggerResponse."""

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
    def snapshots(self) -> list["PipelineSnapshotResponse"]:
        """Implements the 'snapshots' property.

        Returns:
            A list of source snapshots the triggers is attached to.
        """
        return self.get_resources().snapshots

    @property
    def executable_snapshots(self) -> list["PipelineSnapshotResponse"]:
        """Implements the 'executable_snapshots' property.

        Returns:
            A list of snapshots the triggers is attached to.
        """
        return self.get_resources().executable_snapshots

    @property
    def latest_run(self) -> Optional["PipelineRunResponse"]:
        """Implements the 'latest_run' property.

        Returns:
            The latest run of the trigger.
        """
        return self.get_resources().latest_run

    @property
    def concurrency(self) -> TriggerRunConcurrency:
        """Implements the 'concurrency' property.

        Returns:
            The concurrency of the trigger.
        """
        return self.get_body().concurrency


class ScheduleTriggerResponse(TriggerResponse[ScheduleTriggerResponseBody,]):
    """Class representing a ScheduleTrigger response."""

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
    def max_runs(self) -> int | None:
        """Implements the 'max_runs' property.

        Returns:
            The scheduler's max runs.
        """
        return self.get_body().max_runs


# ----------- EVENT CLASSES ------------------- #


class SourceEntity(BaseModel):
    """Base class representing a SourceEntity."""

    type: SourceType
    id: UUID


class PlatformEventTrigger(BaseModel):
    """Base class for event-specific parameters."""

    source_entity: SourceEntity
    target_events: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_event_type(self) -> "PlatformEventTrigger":
        """Validates type/event combination.

        Returns:
            The event trigger instance.

        Raises:
            ValueError: If type/event combination is invalid.
        """
        event_enum = PLATFORM_EVENT_REGISTRY[self.source_entity.type]

        for event in self.target_events:
            try:
                event_enum(event)  # type: ignore[abstract]
            except ValueError:
                allowed = [e.value for e in event_enum]
                raise ValueError(
                    f"Invalid event '{event}' for source_type '{self.source_entity.type}'. "
                    f"Allowed events: {allowed}"
                )

        return self


class PlatformEventTriggerRequest(TriggerRequest, PlatformEventTrigger):
    """Class representing a PlatformEventTrigger request."""

    type: Literal[TriggerType.PLATFORM_EVENT] = TriggerType.PLATFORM_EVENT
    flavor: Literal[TriggerFlavor.PLATFORM_EVENT] = (
        TriggerFlavor.PLATFORM_EVENT
    )

    def get_config(self) -> str:
        """Returns the serialized blob of custom trigger fields.

        Returns:
            Json-dump of ScheduleTrigger config.
        """
        return self.model_dump_json(
            include=set(PlatformEventTrigger.model_fields),
        )

    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates and returns extra flat fields.

        Returns:
            A dictionary with extra fields (next occurrence or empty).
        """
        return {
            "source_entity": f"{self.source_entity.type.value}:{self.source_entity.id}",
            "target_events": " ".join(
                f"event:{event}" for event in self.target_events
            ),
        }


class PlatformEventTriggerUpdate(TriggerUpdate, PlatformEventTrigger):
    """Class representing a PlatformEventTrigger update."""

    type: Literal[TriggerType.PLATFORM_EVENT] = TriggerType.PLATFORM_EVENT
    flavor: Literal[TriggerFlavor.PLATFORM_EVENT] = (
        TriggerFlavor.PLATFORM_EVENT
    )

    def get_config(self) -> str:
        """Returns the serialized blob of custom trigger fields.

        Returns:
            Json-dump of ScheduleTrigger config.
        """
        return self.model_dump_json(
            include=set(PlatformEventTrigger.model_fields),
        )

    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates and returns extra flat fields.

        Returns:
            A dictionary with extra fields (next occurrence or empty).
        """
        return {
            "source_entity": f"{self.source_entity.type.value}:{self.source_entity.id}",
            "target_events": " ".join(
                f"event:{event}" for event in self.target_events
            ),
        }


class PlatformEventTriggerResponseBody(
    PlatformEventTrigger, TriggerResponseBody
):
    """Class representing a PlatformEvent trigger response body."""

    def get_extra_fields(self) -> list[str]:
        """Returns the extra fields (e.g. next occurrence).

        Returns:
            The extra fields for the schedule payload.
        """
        return []


class PlatformEventTriggerResponse(
    TriggerResponse[PlatformEventTriggerResponseBody,]
):
    """Class representing a platform event trigger response."""

    @property
    def source_type(self) -> SourceType:
        """Implements the `source_type` property.

        Returns:
            The source entity type.
        """
        return self.get_body().source_entity.type

    @property
    def source_id(self) -> UUID:
        """Implements the `source_id` property.

        Returns:
            The source entity id.
        """
        return self.get_body().source_entity.id

    @property
    def target_events(self) -> list[str]:
        """Implements the `target_events` property.

        Returns:
            The list of events we trigger runs for.
        """
        return self.get_body().target_events


class TriggerExecutionInfo(BaseModel):
    """Class representing a trigger execution information."""

    upstream_run_id: UUID | None = None


TRIGGER_UPDATE_TYPE_UNION: TypeAlias = Annotated[
    ScheduleTriggerUpdate | PlatformEventTriggerUpdate,
    Field(discriminator="type"),
]
TRIGGER_CREATE_TYPE_UNION: TypeAlias = Annotated[
    ScheduleTriggerRequest | PlatformEventTriggerRequest,
    Field(discriminator="type"),
]
TRIGGER_RETURN_TYPE_UNION: TypeAlias = (
    ScheduleTriggerResponse | PlatformEventTriggerResponse
)
