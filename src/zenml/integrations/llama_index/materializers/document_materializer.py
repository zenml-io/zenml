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
"""Implementation of the llama-index document materializer."""

from typing import TYPE_CHECKING, Any, Dict, Type

from llama_index import Document

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.pydantic_materializer import PydanticMaterializer

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType


class LlamaIndexDocumentMaterializer(BaseMaterializer):
    """Handle serialization and deserialization of llama-index documents."""

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    ASSOCIATED_TYPES = (Document,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pydantic_materializer = PydanticMaterializer(**kwargs)

    def load(self, data_type: Type[Document]) -> Any:
        """Reads a llama-index document from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """

        return Document.from_langchain_format(
            self._pydantic_materializer.load(data_type)
        )

    def save(self, data: Document) -> None:
        """Serialize a llama-index document.

        Args:
            data: The data to store.
        """
        lc_doc = data.to_langchain_format()
        self._pydantic_materializer.save(lc_doc)

    def extract_metadata(self, data: Document) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given

        Args:
            data: The BaseModel object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return self._pydantic_materializer.extract_metadata(data)
