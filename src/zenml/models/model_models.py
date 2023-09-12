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
"""Model implementation to support Model WatchTower feature."""

from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from zenml.model import ModelStages
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.pipeline_run_models import PipelineRunResponseModel


class ModelVersionBaseModel(BaseModel):
    """Model Version base model."""

    version: str = Field(
        title="The name of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        title="The description of the model version",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    stage: Optional[str] = Field(
        title="The stage of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    _model_objects: Dict[str, UUID] = Field(
        title="Model Objects linked to the model version",
        default={},
    )
    _artifact_objects: Dict[str, UUID] = Field(
        title="Artifacts linked to the model version",
        default={},
    )
    _deployments: Dict[str, UUID] = Field(
        title="Deployments linked to the model version",
        default={},
    )
    _pipeline_runs: List[UUID] = Field(
        title="Pipeline runs linked to the model version",
        default=[],
    )


class ModelVersionRequestModel(
    ModelVersionBaseModel,
    WorkspaceScopedRequestModel,
):
    """Model Version request model."""

    model: UUID = Field(
        title="The ID of the model containing version",
    )


class ModelVersionResponseModel(
    ModelVersionBaseModel,
    WorkspaceScopedResponseModel,
):
    """Model Version response model."""

    model: "ModelResponseModel" = Field(
        title="The model containing version",
    )

    @staticmethod
    def _fetch_artifacts_from_list(
        artifacts: Dict[str, UUID]
    ) -> Dict[str, ArtifactResponseModel]:
        from zenml.client import Client

        if artifacts:
            return {
                name: Client().get_artifact(a) for name, a in artifacts.items()
            }
        else:
            return {}

    @property
    def model_objects(self) -> Dict[str, ArtifactResponseModel]:
        return self._fetch_artifacts_from_list(self._model_objects)

    @property
    def artifact_objects(self) -> Dict[str, ArtifactResponseModel]:
        return self._fetch_artifacts_from_list(self._artifact_objects)

    @property
    def deployments(self) -> Dict[str, ArtifactResponseModel]:
        return self._fetch_artifacts_from_list(self._deployments)

    @property
    def pipeline_runs(self) -> List[PipelineRunResponseModel]:
        from zenml.client import Client

        return [Client().get_run(pr) for pr in self._pipeline_runs]

    def set_stage(self, stage: ModelStages):
        """Sets Model Version to a desired stage."""
        pass

    # TODO in https://zenml.atlassian.net/browse/OSS-2433
    # def generate_model_card(self, template_name: str) -> str:
    #     """Return HTML/PDF based on input template"""


class ModelVersionFilterModel(WorkspaceScopedFilterModel):
    """Filter Model for Model Version."""

    model_id: Optional[Union[str, UUID]] = Field(
        description="The ID of the Model",
    )
    model_version_name: Optional[str] = Field(
        default=None,
        description="The name of the Model Version",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )


class ModelVersionLinkBaseModel(BaseModel):
    """Model version links base model."""

    name: str = Field(
        title="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact_id: Optional[UUID]
    pipeline_run_id: Optional[UUID]
    model_version_id: UUID
    is_model_object: bool = False
    is_deployment: bool = False

    @validator("model_version_id")
    def validate_links(cls, model_version_id, values):
        artifact_id = values.get("artifact_id", None)
        pipeline_run_id = values.get("pipeline_run_id", None)
        if (artifact_id is None and pipeline_run_id is None) or (
            artifact_id is not None and pipeline_run_id is not None
        ):
            raise ValueError(
                "You must provide only `artifact_id` or only `pipeline_run_id`."
            )
        return model_version_id


class ModelVersionLinkRequestModel(
    ModelVersionLinkBaseModel, WorkspaceScopedRequestModel
):
    """Model version links request model."""


class ModelVersionLinkResponseModel(
    ModelVersionLinkBaseModel, WorkspaceScopedResponseModel
):
    """Model version links response model."""


class ModelConfigBaseModel(BaseModel):
    """Model Config base model."""

    pass


class ModelConfigRequestModel(
    ModelConfigBaseModel,
    WorkspaceScopedRequestModel,
):
    """Model Config request model."""

    pass


class ModelConfigResponseModel(
    ModelConfigBaseModel,
    WorkspaceScopedResponseModel,
):
    """Model Config response model."""

    pass


class ModelBaseModel(BaseModel):
    """Model base model."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    license: Optional[str] = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    audience: Optional[str] = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    use_cases: Optional[str] = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    limitations: Optional[str] = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    trade_offs: Optional[str] = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    ethic: Optional[str] = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    tags: Optional[List[str]] = Field(
        title="Tags associated with the model",
    )


class ModelRequestModel(
    WorkspaceScopedRequestModel,
    ModelBaseModel,
):
    """Model request model."""

    pass


class ModelResponseModel(
    WorkspaceScopedResponseModel,
    ModelBaseModel,
):
    """Model response model."""

    @property
    def versions(self) -> List[ModelVersionResponseModel]:  # type: ignore[empty-body]
        """List all versions of the model."""
        pass

    def get_version(self, version: Optional[str] = None) -> ModelVersionResponseModel:  # type: ignore[empty-body]
        """Get specific version of the model.

        Args:
            version: version number, stage or None for latest version.
        """
        pass


class ModelFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Workspaces."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the Model",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Model"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the Model"
    )


class ModelUpdateModel(BaseModel):
    """Model update model."""

    license: Optional[str]
    description: Optional[str]
    audience: Optional[str]
    use_cases: Optional[str]
    limitations: Optional[str]
    trade_offs: Optional[str]
    ethic: Optional[str]
    tags: Optional[List[str]]
