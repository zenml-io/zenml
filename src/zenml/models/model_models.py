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
"""Model implementation to support Model Control Plane feature."""

import re
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from zenml.constants import RUNNING_MODEL_VERSION
from zenml.enums import ModelStages
from zenml.logger import get_logger
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.models.model_base_model import ModelBaseModel
from zenml.models.pipeline_run_models import PipelineRunResponseModel

logger = get_logger(__name__)


class ModelVersionBaseModel(BaseModel):
    """Model Version base model."""

    name: Optional[str] = Field(
        description="The name of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    number: Optional[int] = Field(
        description="The number of the model version",
    )
    description: Optional[str] = Field(
        description="The description of the model version",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    stage: Optional[str] = Field(
        description="The stage of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ModelVersionRequestModel(
    ModelVersionBaseModel,
    WorkspaceScopedRequestModel,
):
    """Model Version request model."""

    model: UUID = Field(
        description="The ID of the model containing version",
    )


class ModelVersionResponseModel(
    ModelVersionBaseModel,
    WorkspaceScopedResponseModel,
):
    """Model Version response model."""

    model: "ModelResponseModel" = Field(
        description="The model containing version",
    )
    model_object_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Model Objects linked to the model version",
        default={},
    )
    artifact_object_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Artifacts linked to the model version",
        default={},
    )
    deployment_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Deployments linked to the model version",
        default={},
    )
    pipeline_run_ids: Dict[str, UUID] = Field(
        description="Pipeline runs linked to the model version",
        default={},
    )

    @property
    def model_objects(self) -> Dict[str, Dict[str, ArtifactResponseModel]]:
        """Get all model objects linked to this model version.

        Returns:
            Dictionary of Model Objects with versions as Dict[str, ArtifactResponseModel]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.model_object_ids[name].items()
            }
            for name in self.model_object_ids
        }

    @property
    def artifacts(self) -> Dict[str, Dict[str, ArtifactResponseModel]]:
        """Get all artifacts linked to this model version.

        Returns:
            Dictionary of Artifacts with versions as Dict[str, ArtifactResponseModel]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.artifact_object_ids[name].items()
            }
            for name in self.artifact_object_ids
        }

    @property
    def deployments(self) -> Dict[str, Dict[str, ArtifactResponseModel]]:
        """Get all deployments linked to this model version.

        Returns:
            Dictionary of Deployments with versions as Dict[str, ArtifactResponseModel]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.deployment_ids[name].items()
            }
            for name in self.deployment_ids
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

    def _get_linked_object(
        self,
        collection: Dict[str, Dict[str, UUID]],
        name: str,
        version: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> Optional[ArtifactResponseModel]:
        """Get model object linked to this model version.

        Args:
            collection: The collection to search in (one of self.model_object_ids, self.artifact_object_ids, self.deployment_ids)
            name: The name of the model object to retrieve.
            version: The version of the model object to retrieve (None for latest/non-versioned)
            pipeline_name: The name of the pipeline-generated artifact.
            step_name: The name of the step-generated artifact.

        Returns:
            Specific version of object from collection or None

        Raises:
            RuntimeError: If more than one object is found by given keys
        """
        from zenml.client import Client

        client = Client()

        search_pattern = re.compile(
            (pipeline_name or r"(.*)")
            + r"::"
            + (step_name or r"(.*)")
            + r"::"
            + name
        )
        names = []
        for key in collection:
            if search_pattern.match(key):
                names.append(key)
        if len(names) > 1:
            raise RuntimeError(
                f"Found more than one artifact linked to this model version using "
                f"filter: pipeline_name `{pipeline_name}`, step_name `{step_name}`, name `{name}`.\n"
                + str(names)
            )
        if len(names) == 0:
            return None
        name = names[0]
        if version is None:
            version = max(collection[name].keys())
        return client.get_artifact(collection[name][version])

    def get_model_object(
        self,
        name: str,
        version: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> Optional[ArtifactResponseModel]:
        """Get model object linked to this model version.

        Args:
            name: The name of the model object to retrieve.
            version: The version of the model object to retrieve (None for latest/non-versioned)
            pipeline_name: The name of the pipeline-generated artifact.
            step_name: The name of the step-generated artifact.

        Returns:
            Specific version of Model Object or None
        """
        return self._get_linked_object(
            self.model_object_ids, name, version, pipeline_name, step_name
        )

    def get_artifact_object(
        self,
        name: str,
        version: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> Optional[ArtifactResponseModel]:
        """Get artifact linked to this model version.

        Args:
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for latest/non-versioned)
            pipeline_name: The name of the pipeline generated artifact.
            step_name: The name of the step generated artifact.

        Returns:
            Specific version of Artifact or None
        """
        return self._get_linked_object(
            self.artifact_object_ids, name, version, pipeline_name, step_name
        )

    def get_deployment(
        self,
        name: str,
        version: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> Optional[ArtifactResponseModel]:
        """Get deployment linked to this model version.

        Args:
            name: The name of the deployment to retrieve.
            version: The version of the deployment to retrieve (None for latest/non-versioned)
            pipeline_name: The name of the pipeline generated artifact.
            step_name: The name of the step generated artifact.

        Returns:
            Specific version of Deployment or None
        """
        return self._get_linked_object(
            self.deployment_ids, name, version, pipeline_name, step_name
        )

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
        self, stage: Union[str, ModelStages], force: bool = False
    ) -> "ModelVersionResponseModel":
        """Sets this Model Version to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in target stage or raise.

        Returns:
            Model Version as a response model.

        Raises:
            ValueError: if model_stage is not valid.
        """
        stage = getattr(stage, "value", stage)
        if stage not in [stage.value for stage in ModelStages]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
        from zenml.client import Client

        return Client().update_model_version(
            model_version_id=self.id,
            model_version_update_model=ModelVersionUpdateModel(
                model=self.model.id,
                stage=stage,
                force=force,
            ),
        )

    def _update_default_running_version_name(self) -> None:
        """Replace default running version name with a version number product."""
        if self.name != RUNNING_MODEL_VERSION:
            return

        from zenml.client import Client

        Client().update_model_version(
            model_version_id=self.id,
            model_version_update_model=ModelVersionUpdateModel(
                model=self.model.id, name=str(self.number)
            ),
        )
        logger.info(
            f"Updated model version name for `ID:{self.id}` to `{self.number}`"
        )

    # TODO in https://zenml.atlassian.net/browse/OSS-2433
    # def generate_model_card(self, template_name: str) -> str:
    #     """Return HTML/PDF based on input template"""


class ModelVersionFilterModel(WorkspaceScopedFilterModel):
    """Filter Model for Model Version."""

    model_id: Union[str, UUID] = Field(
        description="The ID of the Model",
    )
    name: Optional[Union[str, UUID]] = Field(
        default=None,
        description="The name of the Model Version",
    )
    number: Optional[int] = Field(
        default=None,
        description="The number of the Model Version",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    stage: Optional[Union[str, ModelStages]] = Field(
        description="The model version stage", default=None
    )

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "model_id",
    ]


class ModelVersionUpdateModel(BaseModel):
    """Update Model for Model Version."""

    model: UUID = Field(
        description="The ID of the model containing version",
    )
    stage: Optional[Union[str, ModelStages]] = Field(
        description="Target model version stage to be set", default=None
    )
    force: bool = Field(
        description="Whether existing model version in target stage should be silently archived "
        "or an error should be raised.",
        default=False,
    )
    name: Optional[str] = Field(
        description="Target model version name to be set", default=None
    )

    @validator("stage")
    def _validate_stage(cls, stage: str) -> str:
        stage = getattr(stage, "value", stage)
        if stage not in [stage.value for stage in ModelStages]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
        return stage


class ModelVersionArtifactBaseModel(BaseModel):
    """Model version links with artifact base model."""

    name: Optional[str] = Field(
        description="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_name: Optional[str] = Field(
        description="The name of the pipeline creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    step_name: Optional[str] = Field(
        description="The name of the step creating this artifact.",
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

    overwrite: bool = False


class ModelVersionArtifactResponseModel(
    ModelVersionArtifactBaseModel, WorkspaceScopedResponseModel
):
    """Model version link with artifact response model.

    link_version: The version of the link (always 1 for not versioned links).
    """

    link_version: int


class ModelVersionArtifactFilterModel(WorkspaceScopedFilterModel):
    """Model version pipeline run links filter model."""

    model_id: Union[str, UUID] = Field(
        description="The name or ID of the Model",
    )
    model_version_id: Union[str, UUID] = Field(
        description="The name or ID of the Model Version",
    )
    name: Optional[str] = Field(
        description="The name of the artifact inside model version.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    pipeline_name: Optional[str] = Field(
        description="The name of the pipeline creating this artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    step_name: Optional[str] = Field(
        description="The name of the step creating this artifact.",
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

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "model_id",
        "model_version_id",
        "only_artifacts",
        "only_model_objects",
        "only_deployments",
        "user_id",
        "workspace_id",
        "scope_workspace",
        "updated",
        "id",
    ]


class ModelVersionPipelineRunBaseModel(BaseModel):
    """Model version links with pipeline run base model."""

    name: Optional[str] = Field(
        description="The name of the pipeline run inside model version.",
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

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "model_id",
        "model_version_id",
    ]


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
            .list_model_versions(
                ModelVersionFilterModel(
                    model_id=self.id, workspace_id=self.workspace.id
                )
            )
            .items
        )

    def get_version(
        self, version: Optional[Union[str, int, ModelStages]] = None
    ) -> ModelVersionResponseModel:
        """Get specific version of the model.

        Args:
            version: version name, number, stage or None for latest version.

        Returns:
            The requested model version.
        """
        from zenml.client import Client

        if version is None:
            return Client().get_model_version(model_name_or_id=self.name)
        else:
            return Client().get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_number_or_id=getattr(
                    version, "value", version
                ),
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
