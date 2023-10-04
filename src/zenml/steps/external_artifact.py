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
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Type,
    Union,
)
from uuid import UUID, uuid4

from zenml.client import Client
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.utils import artifact_utils, source_utils

if TYPE_CHECKING:
    from zenml.config.source import Source

    MaterializerClassOrSource = Union[str, "Source", Type["BaseMaterializer"]]

logger = get_logger(__name__)


class ExternalArtifact:
    """External artifacts can be used to provide values as input to ZenML steps.

    ZenML steps accept either artifacts (=outputs of other steps), parameters
    (raw, JSON serializable values) or external artifacts. External artifacts
    can be used to provide any value as input to a step without needing to
    write an additional step that returns this value.

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

    def __init__(
        self,
        value: Any = None,
        id: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        artifact_name: Optional[str] = None,
        materializer: Optional["MaterializerClassOrSource"] = None,
        store_artifact_metadata: bool = True,
        store_artifact_visualizations: bool = True,
    ) -> None:
        """Initializes an external artifact instance.

        The external artifact needs to have either a value associated with it
        that will be uploaded to the artifact store, or reference an artifact
        that is already registered in ZenML. This could be either from a
        previous pipeline run or a previously uploaded external artifact.

        Args:
            value: The artifact value. Either this or an artifact ID must be
                provided.
            id: The ID of an artifact that should be referenced by this external
                artifact. Either this or an artifact value must be provided.
            pipeline_name: Name of a pipeline to search for artifact in latest run.
            artifact_name: Name of an artifact to be searched in latest pipeline run.
            materializer: The materializer to use for saving the artifact value
                to the artifact store. Only used when `value` is provided.
            store_artifact_metadata: Whether metadata for the artifact should
                be stored. Only used when `value` is provided.
            store_artifact_visualizations: Whether visualizations for the
                artifact should be stored. Only used when `value` is provided.
        """
        self._validate_init_params(
            value=value,
            id=id,
            pipeline_name=pipeline_name,
            artifact_name=artifact_name,
        )

        self._value = value
        self._id = id
        self._pipeline_name = pipeline_name
        self._artifact_name = artifact_name
        self._materializer = materializer
        self._store_artifact_metadata = store_artifact_metadata
        self._store_artifact_visualizations = store_artifact_visualizations

    def _validate_init_params(
        self,
        value: Any = None,
        id: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        artifact_name: Optional[str] = None,
    ) -> None:
        """Validate input parameters and raise on bad input.

        Args:
            value: The artifact value. Either this or an artifact ID must be
                provided.
            id: The ID of an artifact that should be referenced by this external
                artifact. Either this or an artifact value must be provided.
            pipeline_name: Name of a pipeline to search for artifact in latest run.
            artifact_name: Name of an artifact to be searched in latest pipeline run.

        Raises:
            ValueError: If all inputs are `None`.
            ValueError: If more than one of `[value,id,(pipeline_name,artifact_name)]`
                is not `None`.
            ValueError: If `pipeline_name` and `artifact_name` are used separately.
        """
        if (value is not None) + (id is not None) + (
            pipeline_name is not None and artifact_name is not None
        ) > 1:
            raise ValueError(
                "Only a value, an ID or pipeline/artifact name pair can be "
                "provided when creating an external artifact."
            )
        elif all(
            v is None for v in [value, id, pipeline_name or artifact_name]
        ):
            raise ValueError(
                "Either a value, an ID or pipeline/artifact name pair can be "
                "provided when creating an external artifact."
            )
        elif (pipeline_name is None) != (artifact_name is None):
            raise ValueError(
                "`pipeline_name` and `artifact_name` can be only provided "
                "together when creating an external artifact."
            )

    def upload_if_necessary(self) -> UUID:
        """Uploads the artifact if necessary.

        This method does one of two things:
        - If an artifact is referenced by ID, it will verify that the artifact
          exists and is in the correct artifact store.
        - Otherwise, the artifact value will be uploaded and published.

        Raises:
            RuntimeError: If the artifact store of the referenced artifact
                is not the same as the one in the active stack.
            RuntimeError: If the URI of the artifact already exists.

        Returns:
            The artifact ID.
        """
        artifact_store_id = Client().active_stack.artifact_store.id

        if self._value:
            logger.info("Uploading external artifact...")
            artifact_name = f"external_{uuid4()}"
            materializer_class = self._get_materializer_class(
                value=self._value
            )

            uri = os.path.join(
                Client().active_stack.artifact_store.path,
                "external_artifacts",
                artifact_name,
            )
            if fileio.exists(uri):
                raise RuntimeError(f"Artifact URI '{uri}' already exists.")
            fileio.makedirs(uri)

            materializer = materializer_class(uri)

            artifact_id = artifact_utils.upload_artifact(
                name=artifact_name,
                data=self._value,
                materializer=materializer,
                artifact_store_id=artifact_store_id,
                extract_metadata=self._store_artifact_metadata,
                include_visualizations=self._store_artifact_visualizations,
            )

            # To avoid duplicate uploads, switch to referencing the uploaded
            # artifact by ID
            self._id = artifact_id
            logger.info(
                "Finished uploading external artifact %s.", artifact_id
            )
        else:
            response = None
            if self._id:
                response = Client().get_artifact(artifact_id=self._id)
            elif self._pipeline_name and self._artifact_name:
                pipeline = Client().get_pipeline(self._pipeline_name)
                for artifact in pipeline.last_successful_run.artifacts:
                    if artifact.name == self._artifact_name:
                        response = artifact
                        break

            if response is None:
                raise RuntimeError(
                    f"Artifact with name `{self._artifact_name}` was not found "
                    f"in last successful run of pipeline `{self._pipeline_name}`. "
                    "Please check your inputs and try again."
                )
            elif response.artifact_store_id != artifact_store_id:
                raise RuntimeError(
                    f"The artifact {response.name} (ID: {response.id}) "
                    "referenced by an external artifact is not stored in the "
                    "artifact store of the active stack. This will lead to "
                    "issues loading the artifact. Please make sure to only "
                    "reference artifacts stored in your active artifact store."
                )
            self._id = response.id

        return self._id

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
        if isinstance(self._materializer, type):
            return self._materializer
        elif self._materializer:
            return source_utils.load_and_validate_class(
                self._materializer, expected_class=BaseMaterializer
            )
        else:
            return materializer_registry[type(value)]
