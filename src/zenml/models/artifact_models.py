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

from typing import Dict, Optional
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field

from zenml.enums import ArtifactType
from zenml.metadata.metadata_types import DType, MetadataType, StorageSize
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH

# ---- #
# BASE #
# ---- #


class ArtifactBaseModel(BaseModel):
    """Base model for artifacts."""

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    artifact_store_id: Optional[UUID]
    type: ArtifactType
    uri: str = Field(
        title="URI of the artifact.", max_length=STR_FIELD_MAX_LENGTH
    )
    materializer: str = Field(
        title="Materializer class to use for this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    data_type: str = Field(
        title="Data type of the artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    metadata: Dict[str, "MetadataType"] = Field(
        default={},
        title="Metadata of the artifact.",
        example={
            "runtime_data_type": DType(np.ndarray),
            "storage_size": StorageSize(735123),
            "shape": (1437, 64),
            "dtype": DType(np.float64),
            "mean": 4.886177800974252,
            "std": 6.00811374129213,
            "min": 0.0,
            "max": 16.0,
        },
    )


# -------- #
# RESPONSE #
# -------- #


class ArtifactResponseModel(ArtifactBaseModel, ProjectScopedResponseModel):
    """Response model for artifacts."""

    producer_step_run_id: Optional[UUID]


# ------- #
# REQUEST #
# ------- #


class ArtifactRequestModel(ArtifactBaseModel, ProjectScopedRequestModel):
    """Request model for artifacts."""
