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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from zenml.model.base_model import ModelBaseModel
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.pipeline_run_models import PipelineRunResponseModel

if TYPE_CHECKING:
    from zenml.model.model_stages import ModelStages


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
    model_object_ids: Dict[str, UUID] = Field(
        title="Model Objects linked to the model version",
        default={},
    )
    artifact_object_ids: Dict[str, UUID] = Field(
        title="Artifacts linked to the model version",
        default={},
    )
    deployment_ids: Dict[str, UUID] = Field(
        title="Deployments linked to the model version",
        default={},
    )
    pipeline_run_ids: Dict[str, UUID] = Field(
        title="Pipeline runs linked to the model version",
        default={},
    )

    @property
    def model_objects(self) -> Dict[str, ArtifactResponseModel]:
        """Get all model objects linked to this version.

        Returns:
            Dictionary of Model Objects as ArtifactResponseModel
        """
        from zenml.client import Client

        return {
            name: Client().get_artifact(a)
            for name, a in self.model_object_ids.items()
        }

    @property
    def artifact_objects(self) -> Dict[str, ArtifactResponseModel]:
        """Get all artifacts linked to this version.

        Returns:
            Dictionary of Artifact Objects as ArtifactResponseModel
        """
        from zenml.client import Client

        return {
            name: Client().get_artifact(a)
            for name, a in self.artifact_object_ids.items()
        }

    @property
    def deployments(self) -> Dict[str, ArtifactResponseModel]:
        """Get all deployments linked to this version.

        Returns:
            Dictionary of Deployments as ArtifactResponseModel
        """
        from zenml.client import Client

        return {
            name: Client().get_artifact(a)
            for name, a in self.deployment_ids.items()
        }

    @property
    def pipeline_runs(self) -> Dict[str, PipelineRunResponseModel]:
        """Get all pipeline runs linked to this version.

        Returns:
            Dictionary of Pipeline Runs as PipelineRunResponseModel
        """
        from zenml.client import Client

        return {
            name: Client().get_pipeline_run(pr)
            for name, pr in self.pipeline_run_ids.items()
        }

    def get_model_object(self, name: str) -> ArtifactResponseModel:
        """Get model object linked to this version.

        Args:
            name: The name of the model object to retrieve.

        Returns:
            Model Object as ArtifactResponseModel
        """
        from zenml.client import Client

        return Client().get_artifact(self.model_object_ids[name])

    def get_artifact_object(self, name: str) -> ArtifactResponseModel:
        """Get artifact linked to this version.

        Args:
            name: The name of the artifact to retrieve.

        Returns:
            Artifact Object as ArtifactResponseModel
        """
        from zenml.client import Client

        return Client().get_artifact(self.artifact_object_ids[name])

    def get_deployment(self, name: str) -> ArtifactResponseModel:
        """Get deployment linked to this version.

        Args:
            name: The name of the deployment to retrieve.

        Returns:
            Deployment as ArtifactResponseModel
        """
        from zenml.client import Client

        return Client().get_artifact(self.deployment_ids[name])

    def get_pipeline_run(self, name: str) -> PipelineRunResponseModel:
        """Get pipeline run linked to this version.

        Args:
            name: The name of the pipeline run to retrieve.

        Returns:
            PipelineRun as PipelineRunResponseModel
        """
        from zenml.client import Client

        return Client().get_pipeline_run(self.pipeline_run_ids[name])

    def set_stage(
        self, stage: Union[str, "ModelStages"], force: bool = False
    ) -> "ModelVersionResponseModel":
        """Sets this Model Version to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in target stage or raise.

        Returns:
            Dictionary of Model Objects as model_version_name_or_id

        Raises:
            ValueError: if model_stage is not valid.
        """
        from zenml.model.model_stages import ModelStages

        stage = getattr(stage, "value", stage)
        if stage not in [stage.value for stage in ModelStages]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
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
    stage: Union[str, "ModelStages"] = Field(
        title="Target model version stage to be set",
    )
    force: bool = Field(
        title="Whether existing model version in target stage should be silently archived "
        "or an error should be raised.",
        default=False,
    )

    @validator("stage")
    def _validate_stage(cls, stage: str) -> str:
        from zenml.model.model_stages import ModelStages

        stage = getattr(stage, "value", stage)
        if stage not in [stage.value for stage in ModelStages]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
        return stage


class ModelVersionArtifactBaseModel(BaseModel):
    """Model version links with artifact base model."""

    name: Optional[str] = Field(
        title="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    artifact: UUID
    model: UUID
    model_version: UUID
    is_model_object: bool = False
    is_deployment: bool = False

    @validator("is_deployment")
    def _validate_is_deployment(
        cls, is_deployment: bool, values: Dict[str, Any]
    ) -> bool:
        is_model_object = values.get("is_model_object", False)
        if is_model_object and is_deployment:
            raise ValueError(
                "Artifact cannot be a model object and deployment at the same time."
            )
        return is_deployment


class ModelVersionArtifactRequestModel(
    ModelVersionArtifactBaseModel, WorkspaceScopedRequestModel
):
    """Model version link with artifact request model."""


class ModelVersionArtifactResponseModel(
    ModelVersionArtifactBaseModel, WorkspaceScopedResponseModel
):
    """Model version link with artifact response model."""


class ModelVersionArtifactFilterModel(WorkspaceScopedFilterModel):
    """Model version pipeline run links filter model."""

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


class ModelVersionPipelineRunBaseModel(BaseModel):
    """Model version links with pipeline run base model."""

    name: Optional[str] = Field(
        title="The name of the pipeline run inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_run: UUID
    model: UUID
    model_version: UUID


class ModelVersionPipelineRunRequestModel(
    ModelVersionPipelineRunBaseModel, WorkspaceScopedRequestModel
):
    """Model version link with pipeline run request model."""


class ModelVersionPipelineRunResponseModel(
    ModelVersionPipelineRunBaseModel, WorkspaceScopedResponseModel
):
    """Model version link with pipeline run response model."""


class ModelVersionPipelineRunFilterModel(WorkspaceScopedFilterModel):
    """Model version pipeline run links filter model."""

    model_id: Union[str, UUID] = Field(
        description="The name or ID of the Model",
    )
    model_version_id: Union[str, UUID] = Field(
        description="The name or ID of the Model Version",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
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
    def versions(self) -> List[ModelVersionResponseModel]:
        """List all versions of the model.

        Returns:
            The list of all model version.
        """
        from zenml.client import Client

        return (
            Client()
            .zen_store.list_model_versions(
                ModelVersionFilterModel(
                    model_id=self.id, workspace_id=self.workspace
                )
            )
            .items
        )

    def get_version(
        self, version: Optional[Union[str, "ModelStages"]] = None
    ) -> ModelVersionResponseModel:
        """Get specific version of the model.

        Args:
            version: version number, stage or None for latest version.

        Returns:
            The requested model version.
        """
        from zenml.client import Client

        zs = Client().zen_store

        if version is None:
            return zs.get_model_version(model_name_or_id=self.name)
        else:
            return zs.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_id=getattr(version, "value", version),
            )


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
