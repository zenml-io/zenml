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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union
from uuid import UUID

from pydantic import Field

from zenml.enums import (
    RunWaitConditionResolution,
    RunWaitConditionStatus,
    RunWaitConditionType,
)
from zenml.models.v2.base.base import (
    BaseUpdate,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    UserScopedRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models import PipelineRunResponse
    from zenml.models.v2.base.filter import AnySchema


class RunWaitConditionRequest(ProjectScopedRequest):
    """Request model for creating wait conditions."""

    run: UUID = Field(title="The pipeline run ID this condition belongs to.")
    name: str = Field(title="The name of the wait condition.")
    type: RunWaitConditionType = Field(title="The wait condition type.")
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


class RunWaitConditionResolveRequest(UserScopedRequest):
    """Request model for resolving wait conditions."""

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

    type: RunWaitConditionType = Field(title="The wait condition type.")
    status: RunWaitConditionStatus = Field(
        title="The current condition status."
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


class RunWaitConditionResponseResources(ProjectScopedResponseResources):
    """Resource model for wait condition responses."""

    run: "PipelineRunResponse" = Field(
        title="Pipeline run associated with this wait condition."
    )


class RunWaitConditionResponse(
    ProjectScopedResponse[
        RunWaitConditionResponseBody,
        RunWaitConditionResponseMetadata,
        RunWaitConditionResponseResources,
    ]
):
    """Response model for run wait conditions."""

    name: str = Field(title="The name of the wait condition.")

    def get_hydrated_version(self) -> "RunWaitConditionResponse":
        """Get the hydrated version of this wait condition.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_run_wait_condition(self.id, hydrate=True)

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
    def run(self) -> "PipelineRunResponse":
        """The `run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().run


class RunWaitConditionFilter(ProjectScopedFilter):
    """Filter model for wait conditions."""

    FILTER_EXCLUDE_FIELDS = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "resolved_by",
    ]
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
    name: Optional[str] = Field(
        default=None, title="Filter by wait condition name."
    )
    resolved_by: Optional[Union[UUID, str]] = Field(
        default=None,
        title="Filter by the name or ID of the user that resolved the condition.",
        union_mode="left_to_right",
    )
    resolved_at: Optional[Union[datetime, str]] = Field(
        default=None,
        title="Filter by the timestamp when the condition was resolved.",
    )
    resolution: Optional[str] = Field(
        default=None,
        title="Filter by condition resolution.",
    )

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_

        from zenml.zen_stores.schemas import RunWaitConditionSchema, UserSchema

        if self.resolved_by:
            resolved_by_filter = and_(
                RunWaitConditionSchema.resolved_by_user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.resolved_by,
                    table=UserSchema,
                    additional_columns=["full_name"],
                ),
            )
            custom_filters.append(resolved_by_filter)

        return custom_filters
