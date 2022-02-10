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

from typing import TYPE_CHECKING, Any, Optional, Type

from zenml.logger import get_logger
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.post_execution.step import StepView

logger = get_logger(__name__)


class ArtifactView:
    """Post-execution artifact class which can be used to read
    artifact data that was created during a pipeline execution.
    """

    def __init__(
        self,
        id_: int,
        type_: str,
        uri: str,
        materializer: str,
        data_type: str,
        metadata_store: "BaseMetadataStore",
        parent_step_id: int,
    ):
        """Initializes a post-execution artifact object.

        In most cases `ArtifactView` objects should not be created manually but
        retrieved from a `StepView` via the `inputs` or `outputs` properties.

        Args:
            id_: The artifact id.
            type_: The type of this artifact.
            uri: Specifies where the artifact data is stored.
            materializer: Information needed to restore the materializer
                that was used to write this artifact.
            data_type: The type of data that was passed to the materializer
                when writing that artifact. Will be used as a default type
                to read the artifact.
            metadata_store: The metadata store which should be used to fetch
                additional information related to this pipeline.
            parent_step_id: The ID of the parent step.
        """
        self._id = id_
        self._type = type_
        self._uri = uri
        self._materializer = materializer
        self._data_type = data_type
        self._metadata_store = metadata_store
        self._parent_step_id = parent_step_id

    @property
    def id(self) -> int:
        """Returns the artifact id."""
        return self._id

    @property
    def type(self) -> str:
        """Returns the artifact type."""
        return self._type

    @property
    def data_type(self) -> str:
        """Returns the data type of the artifact."""
        return self._data_type

    @property
    def uri(self) -> str:
        """Returns the URI where the artifact data is stored."""
        return self._uri

    @property
    def parent_step_id(self) -> int:
        """Returns the ID of the parent step. This need not be equivalent to
        the ID of the producer step."""
        return self._parent_step_id

    @property
    def producer_step(self) -> "StepView":
        """Returns the original StepView that produced the artifact."""
        # TODO [ENG-174]: Replace with artifact.id instead of passing self if
        #  required.
        return self._metadata_store.get_producer_step_from_artifact(self)

    @property
    def is_cached(self) -> bool:
        """Returns True if artifact was cached in a previous run, else False."""
        # self._metadata_store.
        return self.producer_step.id != self.parent_step_id

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
        """

        if not materializer_class:
            try:
                materializer_class = source_utils.load_source_path_class(
                    self._materializer
                )
            except (ModuleNotFoundError, AttributeError) as e:
                logger.error(
                    f"ZenML can not locate and import the materializer module "
                    f"{self._materializer} which was used to write this "
                    f"artifact. If you want to read from it, please provide "
                    f"a 'materializer_class'."
                )
                raise ModuleNotFoundError(e) from e

        if not output_data_type:
            try:
                output_data_type = source_utils.load_source_path_class(
                    self._data_type
                )
            except (ModuleNotFoundError, AttributeError) as e:
                logger.error(
                    f"ZenML can not locate and import the data type of this "
                    f"artifact {self._data_type}. If you want to read "
                    f"from it, please provide a 'output_data_type'."
                )
                raise ModuleNotFoundError(e) from e

        logger.debug(
            "Using '%s' to read '%s' (uri: %s).",
            materializer_class.__qualname__,
            self._type,
            self._uri,
        )

        # TODO [ENG-162]: passing in `self` to initialize the materializer only
        #  works because materializers only require a `.uri` property at the
        #  moment.
        materializer = materializer_class(self)  # type: ignore[arg-type]
        return materializer.handle_input(output_data_type)

    def __repr__(self) -> str:
        """Returns a string representation of this artifact."""
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"type='{self._type}', uri='{self._uri}', "
            f"materializer='{self._materializer}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the
        same artifact."""
        if isinstance(other, ArtifactView):
            return self._id == other._id and self._uri == other._uri
        return NotImplemented
