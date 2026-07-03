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
"""Models representing hook invocations."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus, HookType
from zenml.models.v2.base.filter import (
    DatetimeFilterOption,
    StringFilterOption,
    UUIDFilterOption,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)
from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
from zenml.models.v2.core.logs import LogsResponse
from zenml.models.v2.misc.exception_info import ExceptionInfo

HOOK_NAME_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_.\-]*$"

# ------------------ Request Model ------------------


class HookInvocationRequest(ProjectScopedRequest):
    """Request model for hook invocations."""

    id: UUID = Field(
        default_factory=uuid4,
        title="The ID of the hook invocation.",
    )
    hook_type: HookType = Field(title="The type of the hook invocation.")
    name: Optional[str] = Field(
        default=None,
        title="The name of the hook invocation.",
        max_length=STR_FIELD_MAX_LENGTH,
        pattern=HOOK_NAME_PATTERN,
    )
    status: ExecutionStatus = Field(title="The status of the hook invocation.")
    start_time: datetime = Field(
        title="The start time of the hook invocation.",
    )
    end_time: Optional[datetime] = Field(
        default=None,
        title="The end time of the hook invocation.",
    )
    source: Optional[str] = Field(
        default=None,
        title="The source of the hook function.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this hook invocation belongs to.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the step run that this hook invocation belongs to.",
    )
    outputs: Dict[str, List[UUID]] = Field(
        default_factory=dict,
        title="The IDs of the output artifact versions of the hook invocation.",
    )
    exception_info: Optional[ExceptionInfo] = Field(
        default=None,
        title="The exception information of the hook invocation.",
    )
    logs_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the logs entry to link to the hook invocation.",
    )


# ------------------ Response Model ------------------


class HookInvocationResponseBody(ProjectScopedResponseBody):
    """Response body for hook invocations."""

    hook_type: HookType = Field(title="The type of the hook invocation.")
    status: ExecutionStatus = Field(title="The status of the hook invocation.")
    start_time: datetime = Field(
        title="The start time of the hook invocation.",
    )
    end_time: Optional[datetime] = Field(
        title="The end time of the hook invocation.",
        default=None,
    )
    pipeline_run_id: UUID = Field(
        title="The ID of the pipeline run that this hook invocation belongs to.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the step run that this hook invocation belongs to.",
    )


class HookInvocationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for hook invocations."""

    source: Optional[str] = Field(
        default=None,
        title="The source of the hook function.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    exception_info: Optional[ExceptionInfo] = Field(
        default=None,
        title="The exception information of the hook invocation.",
    )


class HookInvocationResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the hook invocation entity."""

    outputs: Dict[str, List[ArtifactVersionResponse]] = Field(
        title="The output artifact versions of the hook invocation.",
        default_factory=dict,
    )
    log_collection: Optional[List[LogsResponse]] = Field(
        title="Logs associated with this hook invocation.",
        default=None,
    )


class HookInvocationResponse(
    ProjectScopedResponse[
        HookInvocationResponseBody,
        HookInvocationResponseMetadata,
        HookInvocationResponseResources,
    ]
):
    """Response model for hook invocations."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the hook invocation.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "HookInvocationResponse":
        """Get the hydrated version of this hook invocation.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_hook_invocation(self.id)

    # Body and metadata properties

    @property
    def hook_type(self) -> HookType:
        """The `hook_type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().hook_type

    @property
    def status(self) -> ExecutionStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def start_time(self) -> datetime:
        """The `start_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().start_time

    @property
    def end_time(self) -> Optional[datetime]:
        """The `end_time` property.

        Returns:
            the value of the property.
        """
        return self.get_body().end_time

    @property
    def duration(self) -> Optional[timedelta]:
        """The `duration` property.

        Returns:
            The duration of the hook invocation.
        """
        if self.end_time is None or self.start_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def source(self) -> Optional[str]:
        """The `source` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().source

    @property
    def pipeline_run_id(self) -> UUID:
        """The `pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline_run_id

    @property
    def step_run_id(self) -> Optional[UUID]:
        """The `step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().step_run_id

    @property
    def exception_info(self) -> Optional[ExceptionInfo]:
        """The `exception_info` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().exception_info

    @property
    def outputs(self) -> Dict[str, List[ArtifactVersionResponse]]:
        """The `outputs` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().outputs

    @property
    def log_collection(self) -> Optional[List[LogsResponse]]:
        """The `log_collection` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().log_collection


# ------------------ Filter Model ------------------


class HookInvocationFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of hook invocations."""

    pipeline_run_id: UUIDFilterOption = Field(
        default=None,
        description="Pipeline run of this hook invocation",
        union_mode="left_to_right",
    )
    step_run_id: UUIDFilterOption = Field(
        default=None,
        description="Step run of this hook invocation",
        union_mode="left_to_right",
    )
    hook_type: StringFilterOption = Field(
        default=None,
        description="Type of this hook invocation",
    )
    name: StringFilterOption = Field(
        default=None,
        description="Name of this hook invocation",
    )
    status: StringFilterOption = Field(
        default=None,
        description="Status of this hook invocation",
    )
    start_time: DatetimeFilterOption = Field(
        default=None,
        description="Start time of this hook invocation",
        union_mode="left_to_right",
    )
    end_time: DatetimeFilterOption = Field(
        default=None,
        description="End time of this hook invocation",
        union_mode="left_to_right",
    )
