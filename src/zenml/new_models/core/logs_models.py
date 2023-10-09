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
from typing import Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.new_models.base import (
    BaseRequestModel,
    BaseResponseModel,
    BaseResponseModelMetadata,
    hydrated_property,
)

# ------------------ Request Model ------------------


class LogsRequestModel(BaseRequestModel):
    """Request model for logs."""

    uri: str = Field(
        title="The uri of the logs file",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact_store_id: Union[str, UUID] = Field(
        title="The artifact store ID to associate the logs with.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# ------------------ Update Model ------------------

# There is no update models for logs.

# ------------------ Response Model ------------------


class LogsResponseModelMetadata(BaseResponseModelMetadata):
    """Response model for logs."""

    step_run_id: Optional[Union[str, UUID]] = Field(
        title="Step ID to associate the logs with.",
        default=None,
        description="When this is set, pipeline_run_id should be set to None.",
    )
    pipeline_run_id: Optional[Union[str, UUID]] = Field(
        title="Pipeline run ID to associate the logs with.",
        default=None,
        description="When this is set, step_run_id should be set to None.",
    )
    artifact_store_id: Union[str, UUID] = Field(
        title="The artifact store ID to associate the logs with.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class LogsResponseModel(BaseResponseModel):
    """Response model for logs."""

    # Entity fields
    uri: str = Field(
        title="The uri of the logs file",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Metadata related field, method and properties
    metadata: Optional[LogsResponseModelMetadata]

    def get_hydrated_version(self) -> "LogsResponseModelMetadata":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_run_metadata(self.id, hydrate=True)

    @hydrated_property
    def step_run_id(self):
        """The step_run_id property."""
        return self.metadata.step_run_id

    @hydrated_property
    def pipeline_run_id(self):
        """The pipeline_run_id property."""
        return self.metadata.pipeline_run_id

    @hydrated_property
    def artifact_store_id(self):
        """The artifact_store_id property."""
        return self.metadata.artifact_store_id
