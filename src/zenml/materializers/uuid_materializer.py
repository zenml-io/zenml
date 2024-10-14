#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of ZenML's UUID materializer."""

import os
import uuid
from typing import Any, ClassVar, Dict, Optional, Tuple, Type

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "uuid.txt"


class UUIDMaterializer(BaseMaterializer):
    """Materializer to handle UUID objects."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (uuid.UUID,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Define `self.data_path`.

        Args:
            uri: The URI where the artifact data is stored.
            artifact_store: The artifact store where the artifact data is stored.
        """
        super().__init__(uri, artifact_store)
        self.data_path = os.path.join(self.uri, DEFAULT_FILENAME)

    def load(self, _: Type[uuid.UUID]) -> uuid.UUID:
        """Read UUID from artifact store.
        
        Args:
            _: The type of the data to be loaded.
            
        Returns:
            The loaded UUID.
        """
        with self.artifact_store.open(self.data_path, "r") as f:
            uuid_str = f.read().strip()
        return uuid.UUID(uuid_str)

    def save(self, data: uuid.UUID) -> None:
        """Write UUID to artifact store.
        
        Args:
            data: The UUID to be saved.
        """
        with self.artifact_store.open(self.data_path, "w") as f:
            f.write(str(data))

    def extract_metadata(self, data: uuid.UUID) -> Dict[str, MetadataType]:
        """Extract metadata from the UUID.
        
        Args:
            data: The UUID to extract metadata from.
        
        Returns:
            A dictionary of metadata extracted from the UUID.
        """
        return {
            "uuid_version": str(data.version),
            "uuid_variant": data.variant,
            "string_representation": str(data),
        }
