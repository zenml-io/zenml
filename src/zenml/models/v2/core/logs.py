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

from typing import Any, Optional, Union
from uuid import UUID

from pydantic import Field, field_validator

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)

# ------------------ Request Model ------------------


class LogsRequest(BaseRequest):
    """Request model for logs."""

    uri: str = Field(title="The uri of the logs file")

    artifact_store_id: UUID = Field(
        title="The artifact store ID to associate the logs with.",
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
        assert len(str(value)) < TEXT_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {TEXT_FIELD_MAX_LENGTH}"
        )
        return value

    @field_validator("artifact_store_id")
    @classmethod
    def str_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum text length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < STR_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {STR_FIELD_MAX_LENGTH}"
        )
        return value


# ------------------ Update Model ------------------

# There is no update model for logs.

# ------------------ Response Model ------------------


class LogsResponseBody(BaseDatedResponseBody):
    """Response body for logs."""

    uri: str = Field(
        title="The uri of the logs file",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class LogsResponseMetadata(BaseResponseMetadata):
    """Response metadata for logs."""

    step_run_id: Optional[Union[str, UUID]] = Field(
        title="Step ID to associate the logs with.",
        default=None,
        description="When this is set, pipeline_run_id should be set to None.",
        union_mode="left_to_right",
    )
    pipeline_run_id: Optional[Union[str, UUID]] = Field(
        title="Pipeline run ID to associate the logs with.",
        default=None,
        description="When this is set, step_run_id should be set to None.",
        union_mode="left_to_right",
    )
    artifact_store_id: Union[str, UUID] = Field(
        title="The artifact store ID to associate the logs with.",
        union_mode="left_to_right",
    )

    @field_validator("artifact_store_id")
    @classmethod
    def str_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum text length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < STR_FIELD_MAX_LENGTH
        return value


class LogsResponseResources(BaseResponseResources):
    """Class for all resource models associated with the Logs entity."""


class LogsResponse(
    BaseIdentifiedResponse[
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
    def uri(self) -> str:
        """The `uri` property.

        Returns:
            the value of the property.
        """
        return self.get_body().uri

    @property
    def step_run_id(self) -> Optional[Union[str, UUID]]:
        """The `step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().step_run_id

    @property
    def pipeline_run_id(self) -> Optional[Union[str, UUID]]:
        """The `pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_run_id

    @property
    def artifact_store_id(self) -> Union[str, UUID]:
        """The `artifact_store_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().artifact_store_id


# ------------------ Filter Model ------------------

# There is no filter model for logs.
