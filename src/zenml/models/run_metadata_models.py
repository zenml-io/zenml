#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Models representing run metadata."""

from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel

# ---- #
# BASE #
# ---- #


class RunMetadataBaseModel(BaseModel):
    """Base model for run metadata."""

    pipeline_run_id: Optional[UUID] = Field(
        title="The ID of the pipeline run that this metadata belongs to.",
    )
    step_run_id: Optional[UUID]
    artifact_id: Optional[UUID]
    stack_component_id: Optional[UUID]
    key: str = Field(
        title="The key of the metadata.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    value: MetadataType = Field(
        title="The value of the metadata.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    type: MetadataTypeEnum = Field(
        title="The type of the metadata.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class RunMetadataResponseModel(
    RunMetadataBaseModel, WorkspaceScopedResponseModel
):
    """Response model for run metadata."""


# ------ #
# FILTER #
# ------ #


class RunMetadataFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of run metadata."""

    pipeline_run_id: Optional[Union[str, UUID]] = None
    step_run_id: Optional[Union[str, UUID]] = None
    artifact_id: Optional[Union[str, UUID]] = None
    stack_component_id: Optional[Union[str, UUID]] = None
    key: Optional[str] = None
    type: Optional[Union[str, MetadataTypeEnum]] = None


# ------- #
# REQUEST #
# ------- #


class RunMetadataRequestModel(
    RunMetadataBaseModel, WorkspaceScopedRequestModel
):
    """Request model for run metadata."""
