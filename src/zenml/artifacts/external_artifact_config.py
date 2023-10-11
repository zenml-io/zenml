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
"""External artifact definition."""
from typing import TYPE_CHECKING, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel

from zenml.config.source import Source
from zenml.enums import ModelStages
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]

if TYPE_CHECKING:
    from zenml.model.model_config import ModelConfig
    from zenml.models.artifact_models import ArtifactResponseModel


logger = get_logger(__name__)


class ExternalArtifactConfiguration(BaseModel):
    """External artifact configuration.

    Lightweight class to pass in the steps for runtime inference.
    """

    id: Optional[UUID] = None
    pipeline_name: Optional[str] = None
    artifact_name: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[Union[str, int, ModelStages]] = None
    model_artifact_name: Optional[str] = None
    model_artifact_version: Optional[str] = None
    model_artifact_pipeline_name: Optional[str] = None
    model_artifact_step_name: Optional[str] = None

    def _get_artifact_from_pipeline_run(self) -> "ArtifactResponseModel":
        """Get artifact from pipeline run.

        Returns:
            The fetched Artifact.

        Raises:
            RuntimeError: If artifact was not found in pipeline run.
        """
        from zenml.client import Client

        client = Client()

        response = None
        pipeline = client.get_pipeline(self.pipeline_name)  # type: ignore [arg-type]
        for artifact in pipeline.last_successful_run.artifacts:
            if artifact.name == self.artifact_name:
                response = artifact
                break

        if response is None:
            raise RuntimeError(
                f"Artifact with name `{self.artifact_name}` was not found "
                f"in last successful run of pipeline `{self.pipeline_name}`. "
                "Please check your inputs and try again."
            )

        return response

    def _get_artifact_from_model(
        self, model_config: Optional["ModelConfig"] = None
    ) -> "ArtifactResponseModel":
        """Get artifact from Model Control Plane.

        Args:
            model_config: The model containing the model version.

        Returns:
            The fetched Artifact.

        Raises:
            RuntimeError: If artifact was not found in model version
            RuntimeError: If `model_artifact_name` is set, but `model_name` is empty and
                model configuration is missing in @step and @pipeline.
        """
        from zenml.model.model_config import ModelConfig

        if self.model_name is None:
            if model_config is None:
                raise RuntimeError(
                    "ExternalArtifact initiated with `model_artifact_name`, "
                    "but no model config was provided and missing in @step or "
                    "@pipeline definitions."
                )
            self.model_name = model_config.name
            self.model_version = model_config.version

        _model_config = ModelConfig(
            name=self.model_name,
            version=self.model_version,
            suppress_warnings=True,
        )
        model_version = _model_config._get_model_version()

        for artifact_getter in [
            model_version.get_artifact_object,
            model_version.get_model_object,
            model_version.get_deployment,
        ]:
            response = artifact_getter(
                name=self.model_artifact_name,  # type: ignore [arg-type]
                version=self.model_artifact_version,
                pipeline_name=self.model_artifact_pipeline_name,
                step_name=self.model_artifact_step_name,
            )
            if response is not None:
                break

        if response is None:
            raise RuntimeError(
                f"Artifact with name `{self.model_artifact_name}` was not found "
                f"in model `{self.model_name}` version `{self.model_version}`. "
                "Please check your inputs and try again."
            )

        return response

    def get_artifact_id(
        self, model_config: Optional["ModelConfig"] = None
    ) -> UUID:
        """Get the artifact.

        - If an artifact is referenced by ID, it will verify that the artifact
          exists and is in the correct artifact store.
        - If an artifact is referenced by pipeline and artifact name pair, it
            will be searched in the artifact store by the referenced pipeline.
        - If an artifact is referenced by model name and model version, it will
            be searched in the artifact store by the referenced model.

        Args:
            model_config: The model config of the step (from step or pipeline).

        Returns:
            The artifact ID.

        Raises:
            RuntimeError: If the artifact store of the referenced artifact
                is not the same as the one in the active stack.
            RuntimeError: If the URI of the artifact already exists.
            RuntimeError: If `model_artifact_name` is set, but `model_name` is empty and
                model configuration is missing in @step and @pipeline.
            RuntimeError: If no value, id, pipeline/artifact name pair or model name/model version/model
                artifact name group is provided when creating an external artifact.
        """
        from zenml.client import Client

        client = Client()

        if self.id:
            response = client.get_artifact(artifact_id=self.id)
        elif self.pipeline_name and self.artifact_name:
            response = self._get_artifact_from_pipeline_run()
        elif self.model_artifact_name:
            response = self._get_artifact_from_model(model_config)
        else:
            raise RuntimeError(
                "Either an ID, pipeline/artifact name pair or "
                "model name/model version/model artifact name group can be "
                "provided when creating an external artifact configuration.\n"
                "Potential root cause: you instantiated an ExternalArtifact and "
                "called this method before `upload_by_value` was called."
            )

        artifact_store_id = client.active_stack.artifact_store.id
        if response.artifact_store_id != artifact_store_id:
            raise RuntimeError(
                f"The artifact {response.name} (ID: {response.id}) "
                "referenced by an external artifact is not stored in the "
                "artifact store of the active stack. This will lead to "
                "issues loading the artifact. Please make sure to only "
                "reference artifacts stored in your active artifact store."
            )

        self.id = response.id

        return self.id
