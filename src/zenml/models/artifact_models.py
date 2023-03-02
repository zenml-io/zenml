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

from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import ArtifactType
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel

if TYPE_CHECKING:
    from zenml.models.run_metadata_models import RunMetadataResponseModel

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


class ArtifactResponseModel(ArtifactBaseModel, WorkspaceScopedResponseModel):
    """Response model for artifacts."""

    producer_step_run_id: Optional[UUID]
    metadata: Dict[str, "RunMetadataResponseModel"] = Field(
        default={}, title="Metadata of the artifact."
    )


# ------ #
# FILTER #
# ------ #


class ArtifactFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Artifacts."""

    # `only_unused` refers to a property of the artifacts relationship
    #  rather than a field in the db, hence it needs to be handled
    #  explicitly
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
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
    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace for this artifact"
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


class ArtifactRequestModel(ArtifactBaseModel, WorkspaceScopedRequestModel):
    """Request model for artifacts."""
