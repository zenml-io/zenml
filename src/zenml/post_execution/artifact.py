#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Initialization for the post-execution artifact class."""

from typing import TYPE_CHECKING, Any, Optional, Type
from uuid import UUID

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models import ArtifactResponseModel


logger = get_logger(__name__)


class ArtifactView:
    """Post-execution artifact class.

    This can be used to read artifact data that was created during a pipeline
    execution.
    """

    def __init__(self, model: "ArtifactResponseModel"):
        """Initializes a post-execution artifact object.

        In most cases `ArtifactView` objects should not be created manually but
        retrieved from a `StepView` via the `inputs` or `outputs` properties.

        Args:
            model: The model to initialize this object from.
        """
        self._model = model

    @property
    def id(self) -> UUID:
        """Returns the artifact id.

        Returns:
            The artifact id.
        """
        return self._model.id

    @property
    def name(self) -> str:
        """Returns the name of the artifact (output name in the parent step).

        Returns:
            The name of the artifact.
        """
        return self._model.name

    @property
    def type(self) -> str:
        """Returns the artifact type.

        Returns:
            The artifact type.
        """
        return self._model.type

    @property
    def data_type(self) -> str:
        """Returns the data type of the artifact.

        Returns:
            The data type of the artifact.
        """
        return self._model.data_type

    @property
    def uri(self) -> str:
        """Returns the URI where the artifact data is stored.

        Returns:
            The URI where the artifact data is stored.
        """
        return self._model.uri

    @property
    def materializer(self) -> str:
        """Returns the materializer that was used to write this artifact.

        Returns:
            The materializer that was used to write this artifact.
        """
        return self._model.materializer

    @property
    def producer_step_id(self) -> Optional[UUID]:
        """Returns the ID of the original step that produced the artifact.

        Returns:
            The ID of the original step that produced the artifact.
        """
        return self._model.producer_step_run_id

    def read(
        self,
        output_data_type: Optional[Type[Any]] = None,
        materializer_class: Optional[Type["BaseMaterializer"]] = None,
    ) -> Any:
        """Materializes the data stored in this artifact.

        Args:
            output_data_type: Deprecated; will be ignored.
            materializer_class: Deprecated; will be ignored.

        Returns:
            The materialized data.
        """
        if output_data_type is not None:
            logger.warning(
                "The `output_data_type` argument is deprecated and will be "
                "removed in a future release."
            )
        if materializer_class is not None:
            logger.warning(
                "The `materializer_class` argument is deprecated and will be "
                "removed in a future release."
            )

        from zenml.utils.materializer_utils import load_artifact

        return load_artifact(self._model)

    def __repr__(self) -> str:
        """Returns a string representation of this artifact.

        Returns:
            A string representation of this artifact.
        """
        return (
            f"{self.__class__.__qualname__}(id={self.id}, "
            f"type='{self.type}', uri='{self.uri}', "
            f"materializer='{self.materializer}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same artifact.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same artifact, else
            False.
        """
        if isinstance(other, ArtifactView):
            return self.id == other.id and self.uri == other.uri
        return NotImplemented
