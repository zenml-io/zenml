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
from typing import Any, Dict, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import root_validator

from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.config.source import Source
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]


logger = get_logger(__name__)


class ExternalArtifact(ExternalArtifactConfiguration):
    """External artifacts can be used to provide values as input to ZenML steps.

    ZenML steps accept either artifacts (=outputs of other steps), parameters
    (raw, JSON serializable values) or external artifacts. External artifacts
    can be used to provide any value as input to a step without needing to
    write an additional step that returns this value.

    The external artifact needs to have either a value associated with it
    that will be uploaded to the artifact store, or reference an artifact
    that is already registered in ZenML.

    There are several ways to reference an existing artifact:
    - By providing an artifact ID.
    - By providing an artifact name and version. If no version is provided,
        the latest version of that artifact will be used.

    Args:
        value: The artifact value.
        id: The ID of an artifact that should be referenced by this external
            artifact.
        name: Name of an artifact to search. If none of
            `version`, `pipeline_run_name`, or `pipeline_name` are set, the
            latest version of the artifact will be used.
        version: Version of the artifact to search. Only used when `name` is
            provided. Cannot be used together with `model_version`.
        model_version: The model version to search in. Only used when `name`
            is provided. Cannot be used together with `version`.
        materializer: The materializer to use for saving the artifact value
            to the artifact store. Only used when `value` is provided.
        store_artifact_metadata: Whether metadata for the artifact should
            be stored. Only used when `value` is provided.
        store_artifact_visualizations: Whether visualizations for the
            artifact should be stored. Only used when `value` is provided.

    Example:
    ```
    from zenml import step, pipeline
    from zenml.artifacts.external_artifact import ExternalArtifact
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
    materializer: Optional[MaterializerClassOrSource] = None
    store_artifact_metadata: bool = True
    store_artifact_visualizations: bool = True

    @root_validator
    def _validate_all(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        options = [
            values.get(field, None) is not None
            for field in ["value", "id", "name"]
        ]
        if sum(options) > 1:
            raise ValueError(
                "Only one of `value`, `id`, or `name` can be provided when "
                "creating an external artifact."
            )
        elif sum(options) == 0:
            raise ValueError(
                "Either `value`, `id`, or `name` must be provided when "
                "creating an external artifact."
            )
        return values

    def upload_by_value(self) -> UUID:
        """Uploads the artifact by value.

        Returns:
            The uploaded artifact ID.
        """
        from zenml.artifacts.utils import save_artifact

        artifact_name = f"external_{uuid4()}"
        uri = os.path.join("external_artifacts", artifact_name)
        logger.info("Uploading external artifact to '%s'.", uri)

        artifact = save_artifact(
            name=artifact_name,
            data=self.value,
            extract_metadata=self.store_artifact_metadata,
            include_visualizations=self.store_artifact_visualizations,
            materializer=self.materializer,
            uri=uri,
            has_custom_name=False,
            manual_save=False,
        )

        # To avoid duplicate uploads, switch to referencing the uploaded
        # artifact by ID
        self.id = artifact.id
        self.value = None

        logger.info("Finished uploading external artifact %s.", self.id)
        return self.id

    @property
    def config(self) -> ExternalArtifactConfiguration:
        """Returns the lightweight config without hard for JSON properties.

        Returns:
            The config object to be evaluated in runtime by step interface.
        """
        return ExternalArtifactConfiguration(
            id=self.id,
            name=self.name,
            version=self.version,
            model_version=self.model_version,
        )
