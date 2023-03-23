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

import os
import sys
from typing import TYPE_CHECKING, Any, Dict, Type

from zenml.enums import ArtifactType
from zenml.integrations.langchain.materializers.document_materializer import (
    LangchainDocumentMaterializer,
)
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.pydantic_materializer import DEFAULT_FILENAME
from zenml.utils import yaml_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType


if TYPE_CHECKING and sys.version_info < (3, 8):
    Document = Any
    LCDocument = Any
else:
    from langchain.docstore.document import Document as LCDocument
    from llama_index.readers.schema.base import Document


class LlamaIndexDocumentMaterializer(BaseMaterializer):
    """Handle serialization and deserialization of llama-index documents."""

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    ASSOCIATED_TYPES = (Document,)

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the llama-index document materializer.

        Args:
            **kwargs: Keyword arguments.
        """
        super().__init__(**kwargs)
        self._langchain_materializer = LangchainDocumentMaterializer(**kwargs)

    def load(self, data_type: Type[Document]) -> Document:
        """Reads a llama-index document from JSON.

        Args:
            data_type: The type of the data to read.

        Returns:
            The data read.
        """
        contents = super().load(data_type)
        data_path = os.path.join(self.uri, DEFAULT_FILENAME)
        contents = yaml_utils.read_json(data_path)
        langchain_document = LCDocument.parse_raw(contents)
        return Document.from_langchain_format(langchain_document)

    def save(self, data: Document) -> None:
        """Serialize a llama-index document as a Langchain document.

        Args:
            data: The data to store.
        """
        super().save(data)
        lc_doc = data.to_langchain_format()
        self._langchain_materializer.save(lc_doc)

    def extract_metadata(self, data: Document) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given Llama Index document.

        Args:
            data: The BaseModel object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return self._langchain_materializer.extract_metadata(
            data.to_langchain_format()
        )
