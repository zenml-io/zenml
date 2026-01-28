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
"""Models representing logs."""

from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

# ------------------ Request Model ------------------


class LogsRequest(ProjectScopedRequest):
    """Request model for logs."""

    id: UUID = Field(
        default_factory=uuid4,
        title="The unique id.",
    )
    uri: Optional[str] = Field(
        default=None,
        title="The URI of the logs file (for artifact store logs)",
    )
    # TODO: Remove default value when not supporting clients <0.84.0 anymore
    source: str = Field(default="", title="The source of the logs file")
    artifact_store_id: Optional[UUID] = Field(
        default=None,
        title="The artifact store ID (for artifact store logs)",
    )
    log_store_id: Optional[UUID] = Field(
        default=None,
        title="The log store ID that collected these logs",
    )
    pipeline_run_id: Optional[UUID] = Field(
        default=None,
        title="The pipeline run ID to associate the logs with.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The step run ID to associate the logs with.",
    )

    @field_validator("uri")
    @classmethod
    def text_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum text length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        if value is not None:
            assert len(str(value)) < TEXT_FIELD_MAX_LENGTH, (
                "The length of the value for this field can not "
                f"exceed {TEXT_FIELD_MAX_LENGTH}"
            )
        return value

    @model_validator(mode="after")
    def validate_stack_component_ids(self) -> "LogsRequest":
        """Validate the stack component IDs.

        Raises:
            ValueError: If both `artifact_store_id` and `log_store_id` are not set.

        Returns:
            self
        """
        if self.artifact_store_id is None and self.log_store_id is None:
            raise ValueError(
                "Either an `artifact_store_id` or a `log_store_id` must be set."
            )
        return self

    @model_validator(mode="after")
    def validate_pipeline_id_and_step_id(self) -> "LogsRequest":
        """Validate the log key.

        Returns:
            self

        Raises:
            ValueError: If two different IDs are set at the same time.
        """
        if self.step_run_id and self.pipeline_run_id:
            raise ValueError(
                "Two different IDs can not be set at the same time."
            )
        return self


# ------------------ Update Model ------------------


class LogsUpdate(BaseUpdate):
    """Update model for logs."""

    pipeline_run_id: Optional[UUID] = Field(
        default=None,
        title="The pipeline run ID to associate the logs with.",
    )
    step_run_id: Optional[UUID] = Field(
        default=None,
        title="The step run ID to associate the logs with.",
    )

    @model_validator(mode="after")
    def validate_pipeline_id_and_step_id(self) -> "LogsUpdate":
        """Validate the log key.

        Returns:
            self

        Raises:
            ValueError: If two different IDs are set at the same time.
        """
        if self.step_run_id and self.pipeline_run_id:
            raise ValueError(
                "Two different IDs can not be set at the same time."
            )
        return self


# ------------------ Response Model ------------------


class LogsResponseBody(ProjectScopedResponseBody):
    """Response body for logs."""

    uri: Optional[str] = Field(
        default=None,
        title="The URI of the logs file (for artifact store logs)",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source: str = Field(
        title="The source of the logs file",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class LogsResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for logs."""

    step_run_id: Optional[UUID] = Field(
        title="Step ID to associate the logs with.",
        default=None,
        description="When this is set, pipeline_run_id should be set to None.",
    )
    pipeline_run_id: Optional[UUID] = Field(
        title="Pipeline run ID to associate the logs with.",
        default=None,
        description="When this is set, step_run_id should be set to None.",
    )
    artifact_store_id: Optional[UUID] = Field(
        default=None,
        title="The artifact store ID that collected these logs",
    )
    log_store_id: Optional[UUID] = Field(
        default=None,
        title="The log store ID that collected these logs",
    )


class LogsResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the Logs entity."""


class LogsResponse(
    ProjectScopedResponse[
        LogsResponseBody, LogsResponseMetadata, LogsResponseResources
    ]
):
    """Response model for logs."""

    def get_hydrated_version(self) -> "LogsResponse":
        """Get the hydrated version of these logs.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_logs(self.id)

    # Body and metadata properties
    @property
    def uri(self) -> Optional[str]:
        """The `uri` property.

        Returns:
            the value of the property.
        """
        return self.get_body().uri

    @property
    def source(self) -> str:
        """The `source` property.

        Returns:
            the value of the property.
        """
        return self.get_body().source

    @property
    def step_run_id(self) -> Optional[UUID]:
        """The `step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().step_run_id

    @property
    def pipeline_run_id(self) -> Optional[UUID]:
        """The `pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_run_id

    @property
    def artifact_store_id(self) -> Optional[UUID]:
        """The `artifact_store_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().artifact_store_id

    @property
    def log_store_id(self) -> Optional[UUID]:
        """The `log_store_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().log_store_id


# ------------------ Filter Model ------------------

# There is no filter model for logs.
