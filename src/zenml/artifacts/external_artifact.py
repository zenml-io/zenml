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
from typing import Any, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, PrivateAttr

from zenml.config.source import Source
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]


logger = get_logger(__name__)


class ExternalArtifact(BaseModel):
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

    value: Any
    _id: Optional[UUID] = PrivateAttr(None)
    materializer: Optional[MaterializerClassOrSource] = None
    store_artifact_metadata: bool = True
    store_artifact_visualizations: bool = True

    def upload_by_value(self) -> UUID:
        """Uploads the artifact by value.

        Returns:
            The uploaded artifact ID.

        Raises:
            RuntimeError: If the artifact value is not set.
        """
        if self.value:
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
            self._id = artifact.id
            self.value = None

            logger.info("Finished uploading external artifact %s.", self._id)
        elif self._id is None:
            raise RuntimeError("Cannot upload an empty artifact.")
        return self._id
