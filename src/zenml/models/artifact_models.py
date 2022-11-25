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

from pydantic import BaseModel

from zenml.enums import ArtifactType
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)

# ---- #
# BASE #
# ---- #


class ArtifactBaseModel(BaseModel):
    """Base model for artifacts."""

    name: str  # Name of the output in the parent step
    artifact_store_id: Optional[UUID]
    type: ArtifactType
    uri: str
    materializer: str
    data_type: str


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
