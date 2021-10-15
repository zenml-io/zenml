#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import Any, Optional, Type

from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import source_utils

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
        """
        self._id = id_
        self._type = type_
        self._uri = uri
        self._materializer = materializer

    @property
    def type(self) -> str:
        """Returns the artifact type."""
        return self._type

    @property
    def uri(self) -> str:
        """Returns the URI where the artifact data is stored."""
        return self._uri

    # TODO [MEDIUM]: can we store a default datatype inside the metadata store
    def read(
        self,
        output_data_type: Type,
        materializer_class: Optional[Type[BaseMaterializer]] = None,
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
            materializer_class = source_utils.load_source_path_class(
                self._materializer
            )

        logger.debug(
            "Using '%s' to read '%s' (uri: %s).",
            materializer_class.__qualname__,
            self._type,
            self._uri,
        )

        # TODO [MEDIUM]: passing in `self` to initialize the materializer only
        #  works because materializers only require a `.uri` property at the
        #  moment.
        return materializer_class(self).handle_input(output_data_type)

    def __repr__(self) -> str:
        """Returns a string representation of this artifact."""
        return (
            f"{self.__class__.__qualname__}(id={self._id}, "
            f"type='{self._type}', uri='{self._uri}', "
            f"materializer='{self._materializer}')"
        )
