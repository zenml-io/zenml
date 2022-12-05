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
"""Models representing artifacts."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import ArtifactType
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import (
    MODEL_METADATA_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
    MODEL_URI_FIELD_MAX_LENGTH,
)

# ---- #
# BASE #
# ---- #


class ArtifactBaseModel(BaseModel):
    """Base model for artifacts."""

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    parent_step_id: UUID
    producer_step_id: UUID

    type: ArtifactType
    uri: str = Field(
        title="URI of the artifact.", max_length=MODEL_URI_FIELD_MAX_LENGTH
    )
    materializer: str = Field(
        title="Materializer class to use for this artifact.",
        max_length=MODEL_METADATA_FIELD_MAX_LENGTH,
    )
    data_type: str = Field(
        title="Data type of the artifact.",
        max_length=MODEL_METADATA_FIELD_MAX_LENGTH,
    )
    is_cached: bool

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: Optional[int]
    mlmd_parent_step_id: Optional[int]
    mlmd_producer_step_id: Optional[int]


# -------- #
# RESPONSE #
# -------- #


class ArtifactResponseModel(ArtifactBaseModel, BaseResponseModel):
    """Response model for artifacts."""


# ------- #
# REQUEST #
# ------- #


class ArtifactRequestModel(ArtifactBaseModel, BaseRequestModel):
    """Request model for artifacts."""


# ------ #
# UPDATE #
# ------ #


@update_model
class ArtifactUpdateModel(ArtifactRequestModel):
    """Update model for artifacts."""
