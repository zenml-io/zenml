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
"""Models representing pipeline run wait conditions."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.enums import (
    RunWaitConditionResolution,
    RunWaitConditionStatus,
    RunWaitConditionType,
)
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseUpdate,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse


class RunWaitConditionRequest(ProjectScopedRequest):
    """Request model for creating wait conditions."""

    run_id: UUID = Field(
        title="The pipeline run ID this condition belongs to."
    )
    type: RunWaitConditionType = Field(title="The wait condition type.")
    wait_condition_key: str = Field(
        title="Deterministic key identifying this condition within a run."
    )
    question: Optional[str] = Field(
        default=None,
        title="Optional question shown to external actors.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        title="Optional additional context for the wait condition.",
    )
    data_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Optional JSON Schema describing the expected output value.",
    )
    upstream_step_names: List[str] = Field(
        default_factory=list,
        title="Upstream step names used for DAG control-edge rendering.",
    )
    downstream_step_names: List[str] = Field(
        default_factory=list,
        title="Downstream step names used for DAG control-edge rendering.",
    )


class RunWaitConditionResolveRequest(BaseRequest):
    """Request model for resolving wait conditions."""

    status: RunWaitConditionStatus = Field(
        default=RunWaitConditionStatus.RESOLVED,
        title="Target status for the condition resolution.",
    )
    resolution: RunWaitConditionResolution = Field(
        title="Resolution semantic for the waiting branch.",
    )
    result: Optional[Any] = Field(
        default=None,
        title="Optional resolved result value.",
    )


class RunWaitConditionLeaseUpdate(BaseUpdate):
    """Lease update model for wait conditions."""

    poller_instance_id: str = Field()
    poller_lease_expires_at: datetime = Field()


class RunWaitConditionResponseBody(ProjectScopedResponseBody):
    """Body model for wait condition responses."""

    run_id: UUID = Field(title="The owning pipeline run ID.")
    type: RunWaitConditionType = Field(title="The wait condition type.")
    status: RunWaitConditionStatus = Field(
        title="The current condition status."
    )
    wait_condition_key: str = Field(
        title="Deterministic key identifying this condition within a run."
    )
    last_polled_at: Optional[datetime] = Field(
        default=None, title="Last lease/poll refresh timestamp."
    )
    poller_instance_id: Optional[str] = Field(
        default=None, title="Instance ID of the active poller."
    )
    poller_lease_expires_at: Optional[datetime] = Field(
        default=None, title="Lease expiration timestamp for poll liveness."
    )
    resolved_at: Optional[datetime] = Field(
        default=None, title="Timestamp when the condition was resolved."
    )
    resolved_by_user_id: Optional[UUID] = Field(
        default=None, title="User that resolved the condition."
    )


class RunWaitConditionResponseMetadata(ProjectScopedResponseMetadata):
    """Metadata model for wait condition responses."""

    question: Optional[str] = Field(
        default=None, title="User-facing question text."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        title="Optional additional wait-condition context.",
    )
    data_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        title="Optional JSON schema.",
    )
    resolution: Optional[RunWaitConditionResolution] = Field(
        default=None, title="Optional condition resolution."
    )
    result: Optional[Any] = Field(
        default=None,
        title="Optional resolved result value.",
    )
    upstream_step_names: List[str] = Field(
        default_factory=list,
        title="Upstream step anchors for the DAG control node.",
    )
    downstream_step_names: List[str] = Field(
        default_factory=list,
        title="Downstream step anchors for the DAG control node.",
    )


class RunWaitConditionResponseResources(ProjectScopedResponseResources):
    """Resource model for wait condition responses."""

    run: Optional["PipelineRunResponse"] = Field(
        default=None, title="Pipeline run associated with this wait condition."
    )


class RunWaitConditionResponse(
    ProjectScopedResponse[
        RunWaitConditionResponseBody,
        RunWaitConditionResponseMetadata,
        RunWaitConditionResponseResources,
    ]
):
    """Response model for run wait conditions."""

    @property
    def run_id(self) -> UUID:
        """The `run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().run_id

    @property
    def type(self) -> RunWaitConditionType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def status(self) -> RunWaitConditionStatus:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def wait_condition_key(self) -> str:
        """The `wait_condition_key` property.

        Returns:
            the value of the property.
        """
        return self.get_body().wait_condition_key

    @property
    def last_polled_at(self) -> Optional[datetime]:
        """The `last_polled_at` property.

        Returns:
            the value of the property.
        """
        return self.get_body().last_polled_at

    @property
    def poller_instance_id(self) -> Optional[str]:
        """The `poller_instance_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().poller_instance_id

    @property
    def poller_lease_expires_at(self) -> Optional[datetime]:
        """The `poller_lease_expires_at` property.

        Returns:
            the value of the property.
        """
        return self.get_body().poller_lease_expires_at

    @property
    def resolved_at(self) -> Optional[datetime]:
        """The `resolved_at` property.

        Returns:
            the value of the property.
        """
        return self.get_body().resolved_at

    @property
    def resolved_by_user_id(self) -> Optional[UUID]:
        """The `resolved_by_user_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().resolved_by_user_id

    @property
    def question(self) -> Optional[str]:
        """The `question` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().question

    @property
    def wait_metadata(self) -> Dict[str, Any]:
        """The `wait_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().metadata

    @property
    def data_schema(self) -> Optional[Dict[str, Any]]:
        """The `data_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().data_schema

    @property
    def resolution(self) -> Optional[RunWaitConditionResolution]:
        """The `resolution` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().resolution

    @property
    def result(self) -> Optional[Any]:
        """The `result` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().result

    @property
    def upstream_step_names(self) -> List[str]:
        """The `upstream_step_names` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().upstream_step_names

    @property
    def downstream_step_names(self) -> List[str]:
        """The `downstream_step_names` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().downstream_step_names

    @property
    def run(self) -> Optional["PipelineRunResponse"]:
        """The `run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().run


class RunWaitConditionFilter(ProjectScopedFilter):
    """Filter model for wait conditions."""

    FILTER_EXCLUDE_FIELDS = [*ProjectScopedFilter.FILTER_EXCLUDE_FIELDS]
    CLI_EXCLUDE_FIELDS = [*ProjectScopedFilter.CLI_EXCLUDE_FIELDS]

    run_id: Optional[Union[UUID, str]] = Field(
        default=None,
        title="Filter by pipeline run ID.",
    )
    type: Optional[str] = Field(
        default=None, title="Filter by condition type."
    )
    status: Optional[str] = Field(
        default=None, title="Filter by condition status."
    )
    wait_condition_key: Optional[str] = Field(
        default=None, title="Filter by deterministic wait condition key."
    )
