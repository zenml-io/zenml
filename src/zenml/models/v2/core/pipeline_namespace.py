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
"""Models representing pipeline namespaces."""

from typing import Optional
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import BaseFilter

# ------------------ Request Model ------------------

# There is no request model for pipeline namespaces.

# ------------------ Update Model ------------------

# There is no update model for pipeline namespaces.

# ------------------ Response Model ------------------


class PipelineNamespaceResponseBody(BaseResponseBody):
    """Response body for pipeline namespaces."""

    latest_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the latest run of the pipeline namespace.",
    )
    latest_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        title="The status of the latest run of the pipeline namespace.",
    )


class PipelineNamespaceResponseMetadata(BaseResponseMetadata):
    """Response metadata for pipeline namespaces."""


class PipelineNamespaceResponseResources(BaseResponseResources):
    """Class for all resource models associated with the pipeline namespace entity."""


class PipelineNamespaceResponse(
    BaseResponse[
        PipelineNamespaceResponseBody,
        PipelineNamespaceResponseMetadata,
        PipelineNamespaceResponseResources,
    ]
):
    """Response model for pipeline namespaces."""

    name: str = Field(
        title="The name of the pipeline namespace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineNamespaceResponse":
        """Get the hydrated version of this pipeline namespace.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        return self

    @property
    def latest_run_id(self) -> Optional[UUID]:
        """The `latest_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_id

    @property
    def latest_run_status(self) -> Optional[ExecutionStatus]:
        """The `latest_run_status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_status


# ------------------ Filter Model ------------------


class PipelineNamespaceFilter(BaseFilter):
    """Pipeline namespace filter model."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline namespace.",
    )
