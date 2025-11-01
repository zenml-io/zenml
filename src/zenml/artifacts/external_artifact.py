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
from typing import Any, Union
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.config.source import Source
from zenml.enums import ArtifactSaveType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

MaterializerClassOrSource = Union[str, Source, type[BaseMaterializer]]


logger = get_logger(__name__)


class ExternalArtifact(ExternalArtifactConfiguration):
    """External artifacts can be used to provide values as input to ZenML steps.

    ZenML steps accept either artifacts (=outputs of other steps), parameters
    (raw, JSON serializable values) or external artifacts. External artifacts
    can be used to provide any value as input to a step without needing to
    write an additional step that returns this value.

    The external artifact needs to have a value associated with it
    that will be uploaded to the artifact store.

    Args:
        value: The artifact value.
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

    value: Any | None = None
    materializer: MaterializerClassOrSource | None = Field(
        default=None, union_mode="left_to_right"
    )
    store_artifact_metadata: bool = True
    store_artifact_visualizations: bool = True

    @model_validator(mode="after")
    def external_artifact_validator(self) -> "ExternalArtifact":
        """Model validator for the external artifact.

        Raises:
            ValueError: If an ID was set.

        Returns:
            The validated instance.
        """
        if self.id:
            raise ValueError(
                "External artifacts can only be initialized with a value."
            )

        return self

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
            save_type=ArtifactSaveType.EXTERNAL,
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
        )
