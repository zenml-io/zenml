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
"""Implementation of ZenML's Langchain Document materializer."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Dict, Type

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.pydantic_materializer import PydanticMaterializer

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "data.json"

if TYPE_CHECKING and sys.version_info < (3, 8):
    Document = Any
else:
    from langchain.docstore.document import Document


class LangchainDocumentMaterializer(BaseMaterializer):
    """Handle Langchain Document objects."""

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    ASSOCIATED_TYPES = (Document,)

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the Langchain Document materializer.

        Args:
            **kwargs: Keyword arguments.
        """
        super().__init__(**kwargs)
        self._pydantic_materializer = PydanticMaterializer(**kwargs)

    def load(self, data_type: Type[Document]) -> Any:
        """Reads Langchain Document from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        return self._pydantic_materializer.load(data_type)

    def save(self, data: Document) -> None:
        """Serialize a Langchain Document to JSON.

        Args:
            data: The data to store.
        """
        self._pydantic_materializer.save(data)

    def extract_metadata(self, data: Document) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given Langchain Document object.

        Args:
            data: The Langchain Document object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return self._pydantic_materializer.extract_metadata(data)
