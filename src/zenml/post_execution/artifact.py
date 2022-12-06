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
from zenml.utils import source_utils

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
            output_data_type: The datatype to which the materializer should
                read, will be passed to the materializers `handle_input` method.
            materializer_class: The class of the materializer that should be
                used to read the artifact data. If no materializer class is
                given, we use the materializer that was used to write the
                artifact during execution of the pipeline.

        Returns:
            The materialized data.

        Raises:
            ModuleNotFoundError: If the materializer class could not be found.
        """
        if not materializer_class:
            try:
                materializer_class = source_utils.load_source_path_class(
                    self.materializer
                )
            except (ModuleNotFoundError, AttributeError) as e:
                logger.error(
                    f"ZenML can not locate and import the materializer module "
                    f"{self.materializer} which was used to write this "
                    f"artifact. If you want to read from it, please provide "
                    f"a 'materializer_class'."
                )
                raise ModuleNotFoundError(e) from e

        if not output_data_type:
            try:
                output_data_type = source_utils.load_source_path_class(
                    self.data_type
                )
            except (ModuleNotFoundError, AttributeError) as e:
                logger.error(
                    f"ZenML can not locate and import the data type of this "
                    f"artifact {self.data_type}. If you want to read "
                    f"from it, please provide a 'output_data_type'."
                )
                raise ModuleNotFoundError(e) from e

        logger.debug(
            "Using '%s' to read '%s' (uri: %s).",
            materializer_class.__qualname__,
            self.type,
            self.uri,
        )

        # TODO [ENG-162]: passing in `self` to initialize the materializer only
        #  works because materializers only require a `.uri` property at the
        #  moment.
        materializer = materializer_class(self)  # type: ignore[arg-type]
        return materializer.handle_input(output_data_type)

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
