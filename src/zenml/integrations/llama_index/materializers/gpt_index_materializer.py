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
"""Implementation of the llama-index GPT index materializer."""

# import os
# import sys
# import tempfile
# from typing import (
#     TYPE_CHECKING,
#     Any,
#     ClassVar,
#     Generic,
#     Tuple,
#     Type,
#     TypeVar,
#     cast,
# )

# from zenml.enums import ArtifactType
# from zenml.io import fileio
# from zenml.materializers.base_materializer import BaseMaterializer

# DEFAULT_FILENAME = "index.json"
# DEFAULT_FAISS_FILENAME = "faiss_index.json"

# if TYPE_CHECKING and sys.version_info < (3, 8):
#     BaseGPTIndex = Any
#     GPTFaissIndex = Any
#     T = TypeVar("T", bound=Any)
# else:
#     from llama_index.indices.base import BaseGPTIndex
#     from llama_index.indices.vector_store import GPTFaissIndex

#     T = TypeVar("T", bound=BaseGPTIndex[Any])


# class LlamaIndexGPTIndexMaterializer(Generic[T], BaseMaterializer):
#     """Materializer for llama_index GPT indices."""

#     ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
#     ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (BaseGPTIndex,)

#     def load(self, data_type: Type[T]) -> T:
#         """Loads a llama-index GPT index from disk.

#         Args:
#             data_type: The type of the index.

#         Returns:
#             The index.
#         """
#         filepath = os.path.join(self.uri, DEFAULT_FILENAME)

#         # Create a temporary folder
#         temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
#         temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

#         # Copy from artifact store to temporary file
#         fileio.copy(filepath, temp_file)

#         index = data_type.load_from_disk(save_path=filepath)
#         assert isinstance(index, data_type)

#         # Cleanup and return
#         fileio.rmtree(temp_dir)
#         return index

#     def save(self, index: T) -> None:
#         """Save a llama-index GPT index to disk.

#         Args:
#             index: The index to save.
#         """
#         filepath = os.path.join(self.uri, DEFAULT_FILENAME)

#         with tempfile.NamedTemporaryFile(
#             mode="w", suffix=".json", delete=False
#         ) as f:
#             index.save_to_disk(save_path=f.name)
#             # Copy it into artifact store
#             fileio.copy(f.name, filepath)

#         # Close and remove the temporary file
#         f.close()
#         fileio.remove(f.name)


# class LlamaIndexGPTFaissIndexMaterializer(BaseMaterializer):
#     """Materializer for llama_index GPT faiss indices."""

#     ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
#     ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (GPTFaissIndex,)

#     def load(self, data_type: Type[GPTFaissIndex]) -> GPTFaissIndex:
#         """Load a llama-index GPT faiss index from disk.

#         Args:
#             data_type: The type of the index.

#         Returns:
#             The index.
#         """
#         filepath = os.path.join(self.uri, DEFAULT_FILENAME)
#         faiss_filepath = os.path.join(self.uri, DEFAULT_FAISS_FILENAME)

#         # Create a temporary folder
#         temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
#         temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

#         # Copy from artifact store to temporary file
#         fileio.copy(filepath, temp_file)

#         index = data_type.load_from_disk(
#             save_path=filepath, faiss_index_save_path=faiss_filepath
#         )

#         # Cleanup and return
#         fileio.rmtree(temp_dir)
#         return cast(GPTFaissIndex, index)

#     def save(self, index: GPTFaissIndex) -> None:
#         """Save a llama-index GPT faiss index to disk.

#         Args:
#             index: The index to save.
#         """
#         filepath = os.path.join(self.uri, DEFAULT_FILENAME)
#         faiss_filepath = os.path.join(self.uri, DEFAULT_FAISS_FILENAME)

#         with tempfile.NamedTemporaryFile(
#             mode="w", suffix=".json", delete=False
#         ) as f:
#             index.save_to_disk(
#                 save_path=f.name, faiss_index_save_path=faiss_filepath
#             )
#             # Copy it into artifact store
#             fileio.copy(f.name, filepath)

#         # Close and remove the temporary file
#         f.close()
#         fileio.remove(f.name)
