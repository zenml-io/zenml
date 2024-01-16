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

# import sys
# from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

# from zenml.enums import ArtifactType
# from zenml.integrations.langchain.materializers.document_materializer import (
#     LangchainDocumentMaterializer,
# )

# if TYPE_CHECKING:
#     from zenml.metadata.metadata_types import MetadataType


# if TYPE_CHECKING and sys.version_info < (3, 8):
#     Document = Any
#     LCDocument = Any
# else:
#     from langchain.docstore.document import Document as LCDocument
#     from llama_index.readers.schema.base import Document


# class LlamaIndexDocumentMaterializer(LangchainDocumentMaterializer):
#     """Handle serialization and deserialization of llama-index documents."""

#     ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
#     ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Document,)

#     def load(self, data_type: Type[Any]) -> Any:
#         """Reads a llama-index document from JSON.

#         Args:
#             data_type: The type of the data to read.

#         Returns:
#             The data read.
#         """
#         return Document.from_langchain_format(super().load(LCDocument))

#     def save(self, data: Any) -> None:
#         """Serialize a llama-index document as a Langchain document.

#         Args:
#             data: The data to store.
#         """
#         super().save(data.to_langchain_format())

#     def extract_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
#         """Extract metadata from the given Llama Index document.

#         Args:
#             data: The BaseModel object to extract metadata from.

#         Returns:
#             The extracted metadata as a dictionary.
#         """
#         return super().extract_metadata(data.to_langchain_format())
