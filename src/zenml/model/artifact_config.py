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
"""Artifact Config classes to support Model Control Plane feature."""
from typing import TYPE_CHECKING, ClassVar, Optional, Union
from uuid import UUID

from pydantic import BaseModel, PrivateAttr

from zenml import get_step_context
from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.models.model_models import (
    ModelVersionArtifactFilterModel,
    ModelVersionArtifactRequestModel,
)

if TYPE_CHECKING:
    from zenml.model.model_config import ModelConfig
    from zenml.models import ModelResponseModel, ModelVersionResponseModel


logger = get_logger(__name__)


class ArtifactConfig(BaseModel):
    """Used to link a generic Artifact to the model version.

    model_name: The name of the model to link artifact to.
    model_version: The identifier of the model version to link artifact to.
        It can be exact version ("23"), exact version number (42), stage
        (ModelStages.PRODUCTION) or None for the latest version.
    model_stage: The stage of the model version to link artifact to.
    artifact_name: The override name of a link instead of an artifact name.
    overwrite: Whether to overwrite an existing link or create new versions.
    """

    model_name: Optional[str]
    model_version: Optional[Union[ModelStages, str, int]]
    artifact_name: Optional[str]
    overwrite: bool = False

    _pipeline_name: str = PrivateAttr()
    _step_name: str = PrivateAttr()
    IS_MODEL_ARTIFACT: ClassVar[bool] = False
    IS_DEPLOYMENT_ARTIFACT: ClassVar[bool] = False

    class Config:
        """Config class for ArtifactConfig."""

        smart_union = True

    @property
    def _model_config(self) -> "ModelConfig":
        """Property that returns the model configuration.

        Returns:
            ModelConfig: The model configuration.

        Raises:
            RuntimeError: If model configuration cannot be acquired from @step
                or @pipeline or built on the fly from fields of this class.
        """
        try:
            model_config = get_step_context().model_config
        except StepContextError:
            model_config = None
        # Check if a specific model name is provided and it doesn't match the context name
        if (self.model_name is not None) and (
            model_config is None or model_config.name != self.model_name
        ):
            # Create a new ModelConfig instance with the provided model name and version
            from zenml.model.model_config import ModelConfig

            on_the_fly_config = ModelConfig(
                name=self.model_name,
                version=self.model_version,
                create_new_model_version=False,
                suppress_warnings=True,
            )
            return on_the_fly_config

        if model_config is None:
            raise RuntimeError(
                "No model configuration found in @step or @pipeline. "
                "You can configure ModelConfig inside ArtifactConfig as well, but "
                "`model_name` and `model_version` must be provided."
            )
        # Return the model from the context
        return model_config

    @property
    def _model(self) -> "ModelResponseModel":
        """Get the `ModelResponseModel`.

        Returns:
            ModelResponseModel: The fetched or created model.
        """
        return self._model_config.get_or_create_model()

    @property
    def _model_version(self) -> "ModelVersionResponseModel":
        """Get the `ModelVersionResponseModel`.

        Returns:
            ModelVersionResponseModel: The model version.
        """
        return self._model_config.get_or_create_model_version()

    def _link_to_model_version(
        self,
        artifact_uuid: UUID,
        is_model_object: bool = False,
        is_deployment: bool = False,
    ) -> None:
        """Link artifact to the model version.

        This method is used on exit from the step context to link artifact to the model version.

        Args:
            artifact_uuid: The UUID of the artifact to link.
            is_model_object: Whether the artifact is a model object. Defaults to False.
            is_deployment: Whether the artifact is a deployment. Defaults to False.
        """
        from zenml.client import Client

        # Create a ZenML client
        client = Client()

        artifact_name = self.artifact_name
        if artifact_name is None:
            artifact = client.zen_store.get_artifact(artifact_id=artifact_uuid)
            artifact_name = artifact.name

        # Create a request model for the model version artifact link
        request = ModelVersionArtifactRequestModel(
            user=client.active_user.id,
            workspace=client.active_workspace.id,
            name=artifact_name,
            artifact=artifact_uuid,
            model=self._model.id,
            model_version=self._model_version.id,
            is_model_object=is_model_object,
            is_deployment=is_deployment,
            overwrite=self.overwrite,
            pipeline_name=self._pipeline_name,
            step_name=self._step_name,
        )

        # Create the model version artifact link using the ZenML client
        existing_links = client.list_model_version_artifact_links(
            ModelVersionArtifactFilterModel(
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
                name=artifact_name,
                model_id=self._model.id,
                model_version_id=self._model_version.id,
                only_artifacts=not (is_model_object or is_deployment),
                only_deployments=is_deployment,
                only_model_objects=is_model_object,
            )
        )
        if len(existing_links):
            if self.overwrite:
                # delete all model version artifact links by name
                logger.warning(
                    f"Existing artifact link(s) `{artifact_name}` found and will be deleted."
                )
                client.zen_store.delete_model_version_artifact_link(
                    model_name_or_id=self._model.id,
                    model_version_name_or_id=self._model_version.id,
                    model_version_artifact_link_name_or_id=artifact_name,
                )
            else:
                logger.info(
                    f"Artifact link `{artifact_name}` already exists, adding new version."
                )
        client.zen_store.create_model_version_artifact_link(request)

    def link_to_model(
        self,
        artifact_uuid: UUID,
    ) -> None:
        """Link artifact to the model version.

        Args:
            artifact_uuid (UUID): The UUID of the artifact to link.
        """
        self._link_to_model_version(
            artifact_uuid,
            is_model_object=self.IS_MODEL_ARTIFACT,
            is_deployment=self.IS_DEPLOYMENT_ARTIFACT,
        )


class ModelArtifactConfig(ArtifactConfig):
    """Used to link a Model Object to the model version.

    save_to_model_registry: Whether to save the model object to the model registry.
    """

    save_to_model_registry: bool = True
    IS_MODEL_ARTIFACT = True


class DeploymentArtifactConfig(ArtifactConfig):
    """Used to link a Deployment to the model version."""

    IS_DEPLOYMENT_ARTIFACT = True
