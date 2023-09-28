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
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, root_validator

from zenml.enums import ModelStages
from zenml.io import fileio
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.source import Source
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.model.model_config import ModelConfig
    from zenml.models.artifact_models import ArtifactResponseModel

    MaterializerClassOrSource = Union[str, "Source", Type["BaseMaterializer"]]


logger = get_logger(__name__)


class ExternalArtifact(BaseModel):
    """External artifacts can be used to provide values as input to ZenML steps.

    ZenML steps accept either artifacts (=outputs of other steps), parameters
    (raw, JSON serializable values) or external artifacts. External artifacts
    can be used to provide any value as input to a step without needing to
    write an additional step that returns this value.

    This class can be configured using the following parameters:
    - value: The artifact value (any python object), that will be uploaded to the
        artifact store.
    - id: The ID of an artifact that is already registered in ZenML.
    - pipeline_name & artifact_name: Name of a pipeline and artifact to search in
        latest run.
    - model_name & model_version & model_artifact_name & model_artifact_version: Name of a
        model, model version, model artifact and artifact version to search.

    Args:
        value: The artifact value.

        id: The ID of an artifact that should be referenced by this external
            artifact.

        pipeline_name: Name of a pipeline to search for artifact in latest run.
        artifact_name: Name of an artifact to be searched in latest pipeline run.

        model_name: Name of a model to search for artifact in (if None - derived from step context).
        model_version: Version of a model to search for artifact in (if None - derived from step context).
        model_artifact_name: Name of a model artifact to search for.
        model_artifact_version: Version of a model artifact to search for.

        materializer: The materializer to use for saving the artifact value
            to the artifact store. Only used when `value` is provided.
        store_artifact_metadata: Whether metadata for the artifact should
            be stored. Only used when `value` is provided.
        store_artifact_visualizations: Whether visualizations for the
            artifact should be stored. Only used when `value` is provided.

    Example:
    ```
    from zenml import step, pipeline, ExternalArtifact
    import numpy as np

    @step
    def my_step(value: np.ndarray) -> None:
      print(value)

    my_array = np.array([1, 2, 3])

    @pipeline
    def my_pipeline():
      my_step(value=ExternalArtifact(my_array))
    ```
    """

    value: Optional[Any] = None
    id: Optional[UUID] = None
    pipeline_name: Optional[str] = None
    artifact_name: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    model_artifact_name: Optional[Union[str, "ModelStages"]] = None
    model_artifact_version: Optional[str] = None
    model_artifact_pipeline_name: Optional[str] = None
    model_artifact_step_name: Optional[str] = None
    materializer: Optional["MaterializerClassOrSource"] = None
    store_artifact_metadata: bool = True
    store_artifact_visualizations: bool = True

    @root_validator
    def _validate_all(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        value = values.get("value", None)
        id = values.get("id", None)
        pipeline_name = values.get("pipeline_name", None)
        artifact_name = values.get("artifact_name", None)
        model_name = values.get("model_name", None)
        model_version = values.get("model_version", None)
        model_artifact_name = values.get("model_artifact_name", None)

        if (value is not None) + (id is not None) + (
            pipeline_name is not None and artifact_name is not None
        ) + (model_artifact_name is not None) > 1:
            raise ValueError(
                "Only a value, an ID, pipeline/artifact name pair or "
                "model name/model version/model artifact name group can be "
                "provided when creating an external artifact."
            )
        elif all(
            v is None
            for v in [
                value,
                id,
                pipeline_name or artifact_name,
                model_name or model_version or model_artifact_name,
            ]
        ):
            raise ValueError(
                "Either a value, an ID, pipeline/artifact name pair or "
                "model name/model version/model artifact name group must be "
                "provided when creating an external artifact."
            )
        elif (pipeline_name is None) != (artifact_name is None):
            raise ValueError(
                "`pipeline_name` and `artifact_name` can be only provided "
                "together when creating an external artifact."
            )
        return values

    def _upload_by_value(self) -> UUID:
        """Uploads the artifact by value.

        Returns:
            The uploaded artifact ID.

        Raises:
            RuntimeError: If artifact URI already exists.
        """
        from zenml.client import Client
        from zenml.utils.artifact_utils import upload_artifact

        client = Client()

        artifact_store_id = client.active_stack.artifact_store.id

        logger.info("Uploading external artifact...")
        artifact_name = f"external_{uuid4()}"
        materializer_class = self._get_materializer_class(value=self.value)

        uri = os.path.join(
            client.active_stack.artifact_store.path,
            "external_artifacts",
            artifact_name,
        )
        if fileio.exists(uri):
            raise RuntimeError(f"Artifact URI '{uri}' already exists.")
        fileio.makedirs(uri)

        materializer = materializer_class(uri)

        artifact_id: UUID = upload_artifact(
            name=artifact_name,
            data=self.value,
            materializer=materializer,
            artifact_store_id=artifact_store_id,
            extract_metadata=self.store_artifact_metadata,
            include_visualizations=self.store_artifact_visualizations,
        )

        # To avoid duplicate uploads, switch to referencing the uploaded
        # artifact by ID
        self.id = artifact_id
        # clean-up state after upload done
        self.value = None
        logger.info("Finished uploading external artifact %s.", artifact_id)

        return self.id

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

        # clean-up state after id found
        self.pipeline_name = None
        self.artifact_name = None

        return response

    def _get_artifact_from_model(
        self, model_config: Optional["ModelConfig"] = None
    ) -> "ArtifactResponseModel":
        """Get artifact from Model WatchTower.

        Args:
            model_config: The model containing the model version.

        Returns:
            The fetched Artifact.

        Raises:
            RuntimeError: If artifact was not found in model version
            RuntimeError: If `model_artifact_name` is set, but `model_name` is empty and
                model configuration is missing in @step and @pipeline.
        """
        from zenml.client import Client
        from zenml.model.model_config import ModelConfig

        client = Client()

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
            name=self.model_name, version=self.model_version
        )
        model = client.zen_store.get_model(model_name_or_id=self.model_name)
        model_version = _model_config._get_model_version(model)

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

        # clean-up state after id found
        self.model_name = None
        self.model_version = None
        self.model_artifact_name = None

        return response

    def upload_if_necessary(
        self, model_config: Optional["ModelConfig"] = None
    ) -> UUID:
        """Uploads the artifact if necessary.

        This method does one of two things:
        - If an artifact is referenced by ID, it will verify that the artifact
          exists and is in the correct artifact store.
        - Otherwise, the artifact value will be uploaded and published.

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

        if self.value:
            self.id = self._upload_by_value()
        else:
            if self.id:
                response = client.get_artifact(artifact_id=self.id)
            elif self.pipeline_name and self.artifact_name:
                response = self._get_artifact_from_pipeline_run()
            elif self.model_artifact_name:
                response = self._get_artifact_from_model(model_config)
            else:
                raise RuntimeError(
                    "Either a value, an ID, pipeline/artifact name pair or "
                    "model name/model version/model artifact name group can be "
                    "provided when creating an external artifact."
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

    def _get_materializer_class(self, value: Any) -> Type["BaseMaterializer"]:
        """Gets a materializer class for a value.

        If a custom materializer is defined for this artifact it will be
        returned. Otherwise it will get the materializer class from the
        registry, falling back to the Cloudpickle materializer if no concrete
        materializer is registered for the type of value.

        Args:
            value: The value for which to get the materializer class.

        Returns:
            The materializer class.
        """
        from zenml.materializers.base_materializer import BaseMaterializer
        from zenml.materializers.materializer_registry import (
            materializer_registry,
        )
        from zenml.utils import source_utils

        if isinstance(self.materializer, type):
            return self.materializer
        elif self.materializer:
            return source_utils.load_and_validate_class(
                self.materializer, expected_class=BaseMaterializer
            )
        else:
            return materializer_registry[type(value)]
