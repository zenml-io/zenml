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

from typing import ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import ArtifactType
from zenml.models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ProjectScopedFilterModel

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


# -------- #
# RESPONSE #
# -------- #


class ArtifactResponseModel(ArtifactBaseModel, ProjectScopedResponseModel):
    """Response model for artifacts."""

    producer_step_run_id: Optional[UUID]


# ------ #
# FILTER #
# ------ #


class ArtifactFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced filtering of all Artifacts."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "only_unused",
    ]

    name: str = Field(
        default=None,
        description="Name of the artifact",
    )
    uri: str = Field(
        default=None,
        description="Uri of the artifact",
    )
    materializer: str = Field(
        default=None,
        description="Materializer used to produce the artifact",
    )
    type: str = Field(
        default=None,
        description="Type of the artifact",
    )
    data_type: str = Field(
        default=None,
        description="Datatype of the artifact",
    )
    artifact_store_id: Union[UUID, str] = Field(
        default=None, description="Artifact store for this artifact"
    )
    project_id: Union[UUID, str] = Field(
        default=None, description="Project for this artifact"
    )
    user_id: Union[UUID, str] = Field(
        default=None, description="User that produced this artifact"
    )
    only_unused: bool = Field(
        default=False, description="Filter only for unused artifacts"
    )


# ------- #
# REQUEST #
# ------- #


class ArtifactRequestModel(ArtifactBaseModel, ProjectScopedRequestModel):
    """Request model for artifacts."""


# ------ #
# UPDATE #
# ------ #


@update_model
class ArtifactUpdateModel(ArtifactRequestModel):
    """Update model for artifacts."""
