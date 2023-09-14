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

from typing import Any, Dict, List, Optional, Union
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
        """Get all model objects linked to this version.

        Returns:
            Dictionary of Model Objects as ArtifactResponseModel
        """
        return self._fetch_artifacts_from_list(self._model_objects)

    @property
    def artifact_objects(self) -> Dict[str, ArtifactResponseModel]:
        """Get all artifacts linked to this version.

        Returns:
            Dictionary of Artifact Objects as ArtifactResponseModel
        """
        return self._fetch_artifacts_from_list(self._artifact_objects)

    @property
    def deployments(self) -> Dict[str, ArtifactResponseModel]:
        """Get all deployments linked to this version.

        Returns:
            Dictionary of Deployments as ArtifactResponseModel
        """
        return self._fetch_artifacts_from_list(self._deployments)

    @property
    def pipeline_runs(self) -> List[PipelineRunResponseModel]:
        """Get all pipeline runs linked to this version.

        Returns:
            List of Pipeline Runs as PipelineRunResponseModel
        """
        from zenml.client import Client

        return [Client().get_pipeline_run(pr) for pr in self._pipeline_runs]

    def set_stage(
        self, stage: ModelStages, force: bool = False
    ) -> "ModelVersionResponseModel":
        """Sets this Model Version to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in target stage or raise.

        Returns:
            Dictionary of Model Objects as model_version_name_or_id"""
        from zenml.client import Client

        return Client().zen_store.update_model_version(
            model_version_id=self.id,
            model_version_update_model=ModelVersionUpdateModel(
                model=self.model.id,
                stage=stage,
                force=force,
            ),
        )

    # TODO in https://zenml.atlassian.net/browse/OSS-2433
    # def generate_model_card(self, template_name: str) -> str:
    #     """Return HTML/PDF based on input template"""


class ModelVersionFilterModel(WorkspaceScopedFilterModel):
    """Filter Model for Model Version."""

    model_id: Union[str, UUID] = Field(
        description="The ID of the Model",
    )
    version: Optional[Union[str, UUID]] = Field(
        default=None,
        description="The name of the Model Version",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )


class ModelVersionUpdateModel(BaseModel):
    """Update Model for Model Version."""

    model: UUID = Field(
        title="The ID of the model containing version",
    )
    stage: ModelStages = Field(
        title="Target model version stage to be set",
    )
    force: bool = Field(
        title="Whether existing model version in target stage should be silently archived "
        "or an error should be raised.",
        default=False,
    )


class ModelVersionLinkBaseModel(BaseModel):
    """Model version links base model."""

    name: str = Field(
        title="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact: Optional[UUID]
    pipeline_run: Optional[UUID]
    model: UUID
    model_version: UUID
    is_model_object: bool = False
    is_deployment: bool = False

    @validator("model_version")
    def _validate_links(
        cls, model_version: UUID, values: Dict[str, Any]
    ) -> UUID:
        artifact = values.get("artifact", None)
        pipeline_run = values.get("pipeline_run", None)
        if (artifact is None and pipeline_run is None) or (
            artifact is not None and pipeline_run is not None
        ):
            raise ValueError(
                "You must provide only `artifact` or only `pipeline_run`."
            )
        return model_version


class ModelVersionLinkRequestModel(
    ModelVersionLinkBaseModel, WorkspaceScopedRequestModel
):
    """Model version links request model."""


class ModelVersionLinkResponseModel(
    ModelVersionLinkBaseModel, WorkspaceScopedResponseModel
):
    """Model version links response model."""


class ModelVersionLinkFilterModel(WorkspaceScopedFilterModel):
    """Model version links filter model."""

    model_id: Union[str, UUID] = Field(
        description="The name or ID of the Model",
    )
    model_version_id: Union[str, UUID] = Field(
        description="The name or ID of the Model Version",
    )
    name: Optional[str] = Field(
        title="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    only_artifacts: Optional[bool] = False
    only_model_objects: Optional[bool] = False
    only_deployments: Optional[bool] = False
    only_pipeline_runs: Optional[bool] = False

    @validator("only_pipeline_runs")
    def _validate_flags(
        cls, only_pipeline_runs: bool, values: Dict[str, Any]
    ) -> bool:
        s = int(only_pipeline_runs)
        s += int(values.get("only_artifacts", False))
        s += int(values.get("only_model_objects", False))
        s += int(values.get("only_deployments", False))
        if s > 1:
            raise ValueError(
                "Only one of the selection flags can be used at once."
            )
        return only_pipeline_runs


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
