#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Materializer that stores all artifacts in memory."""

from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
)

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import MetadataType


class InMemoryMaterializer(BaseMaterializer):
    """Materializer that stores artifacts in memory."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (object,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    SKIP_REGISTRATION: ClassVar[bool] = True

    def save(self, data: Any) -> None:
        """Store data in memory.

        Args:
            data: The data to save.
        """
        from zenml.deployers.server import runtime

        runtime.put_in_memory_data(self.uri, data)

    def load(self, data_type: Type[Any]) -> Any:
        """Load data from memory.

        Args:
            data_type: The type of the data to load.

        Returns:
            The loaded data.

        Raises:
            RuntimeError: If no data is available in memory.
        """
        from zenml.deployers.server import runtime

        try:
            return runtime.get_in_memory_data(self.uri)
        except KeyError:
            raise RuntimeError(
                f"No data available for artifactURI `{self.uri}`"
            )

    def extract_full_metadata(self, data: Any) -> Dict[str, MetadataType]:
        """No metadata extraction.

        Args:
            data: The data to extract metadata from.

        Returns:
            Empty metadata dictionary.
        """
        return {}

    def save_visualizations(self, data: Any) -> Dict[str, Any]:
        """No visualizations.

        Args:
            data: The data to save visualizations for.

        Returns:
            Empty visualizations dictionary.
        """
        return {}

    def compute_content_hash(self, data: Any) -> Optional[str]:
        """No content hash computation in serving mode.

        Args:
            data: The data to compute the content hash of.

        Returns:
            None.
        """
        return None
