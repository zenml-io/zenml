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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, PrivateAttr, root_validator

from zenml import get_step_context
from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.model.model_version import ModelVersion


logger = get_logger(__name__)


class DataArtifactConfig(BaseModel):
    """Used to link a data artifact to the model version.

    model_name: The name of the model to link data artifact to.
    model_version: The identifier of the model version to link data artifact to.
        It can be exact version ("23"), exact version number (42), stage
        (ModelStages.PRODUCTION) or ModelStages.LATEST for the latest version.
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
    IS_ENDPOINT_ARTIFACT: ClassVar[bool] = False

    @root_validator
    def _root_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        model_name = values.get("model_name", None)
        if model_name and values.get("model_version", None) is None:
            raise ValueError(
                f"Creation of new model version from `{cls}` is not allowed. "
                "Please either keep `model_name` and `model_version` both "
                "`None` to get the model version from the step context or "
                "specify both at the same time. You can use `ModelStages.LATEST` "
                "as `model_version` when latest model version is desired."
            )
        return values

    class Config:
        """Config class for ArtifactConfig."""

        smart_union = True

    @property
    def _model_version(self) -> "ModelVersion":
        """Property that returns the model version.

        Returns:
            ModelVersion: The model version.

        Raises:
            RuntimeError: If model version cannot be acquired from @step
                or @pipeline or built on the fly from fields of this class.
        """
        try:
            model_version = get_step_context().model_version
        except (StepContextError, RuntimeError):
            model_version = None
        # Check if a specific model name is provided and it doesn't match the context name
        if (self.model_name is not None) and (
            model_version is None or model_version.name != self.model_name
        ):
            # Create a new ModelVersion instance with the provided model name and version
            from zenml.model.model_version import ModelVersion

            on_the_fly_config = ModelVersion(
                name=self.model_name,
                version=self.model_version,
            )
            return on_the_fly_config

        if model_version is None:
            raise RuntimeError(
                "No model version configuration found in @step or @pipeline. "
                "You can configure model version inside ArtifactConfig as well, but "
                "`model_name` and `model_version` must be provided."
            )
        # Return the model from the context
        return model_version

    def _link_to_model_version(
        self,
        artifact_uuid: UUID,
        model_version: "ModelVersion",
        is_model_artifact: bool = False,
        is_endpoint_artifact: bool = False,
    ) -> None:
        """Link artifact to the model version.

        This method is used on exit from the step context to link artifact to the model version.

        Args:
            artifact_uuid: The UUID of the artifact to link.
            model_version: The model version from caller.
            is_model_artifact: Whether the artifact is a model artifact. Defaults to False.
            is_endpoint_artifact: Whether the artifact is an endpoint artifact. Defaults to False.
        """
        from zenml.client import Client
        from zenml.models.model_models import (
            ModelVersionArtifactFilterModel,
            ModelVersionArtifactRequestModel,
        )

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
            model=model_version.model_id,
            model_version=model_version.id,
            is_model_artifact=is_model_artifact,
            is_endpoint_artifact=is_endpoint_artifact,
            overwrite=self.overwrite,
            pipeline_name=self._pipeline_name,
            step_name=self._step_name,
        )

        # Create the model version artifact link using the ZenML client
        existing_links = client.list_model_version_artifact_links(
            model_version_id=model_version.id,
            model_version_artifact_link_filter_model=ModelVersionArtifactFilterModel(
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
                name=artifact_name,
                only_data_artifacts=not (
                    is_model_artifact or is_endpoint_artifact
                ),
                only_endpoint_artifacts=is_endpoint_artifact,
                only_model_artifacts=is_model_artifact,
                pipeline_name=self._pipeline_name,
                step_name=self._step_name,
            ),
        )
        if len(existing_links):
            if self.overwrite:
                # delete all model version artifact links by name
                logger.warning(
                    f"Existing artifact link(s) `{artifact_name}` found and will be deleted."
                )

                client.zen_store.delete_model_version_artifact_link(
                    model_version_id=model_version.id,
                    model_version_artifact_link_name_or_id=artifact_name,
                )
            else:
                logger.info(
                    f"Artifact link `{artifact_name}` already exists, adding new version."
                )
        client.zen_store.create_model_version_artifact_link(request)

    def link_to_model(
        self, artifact_uuid: UUID, model_version: "ModelVersion"
    ) -> None:
        """Link artifact to the model version.

        Args:
            artifact_uuid: The UUID of the artifact to link.
            model_version: The model version from caller.
        """
        self._link_to_model_version(
            artifact_uuid,
            model_version=model_version,
            is_model_artifact=self.IS_MODEL_ARTIFACT,
            is_endpoint_artifact=self.IS_ENDPOINT_ARTIFACT,
        )


class ModelArtifactConfig(DataArtifactConfig):
    """Used to link a model artifact to the model version.

    save_to_model_registry: Whether to save the model artifact to the model registry.
    """

    save_to_model_registry: bool = True
    IS_MODEL_ARTIFACT = True


class EndpointArtifactConfig(DataArtifactConfig):
    """Used to link an endpoint artifact to the model version."""

    IS_ENDPOINT_ARTIFACT = True
