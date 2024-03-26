# #  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License");
# #  you may not use this file except in compliance with the License.
# #  You may obtain a copy of the License at:
# #
# #       https://www.apache.org/licenses/LICENSE-2.0
# #
# #  Unless required by applicable law or agreed to in writing, software
# #  distributed under the License is distributed on an "AS IS" BASIS,
# #  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# #  or implied. See the License for the specific language governing
# #  permissions and limitations under the License.
# """Implementation of the llama-index GPT index materializer."""

# import sys
# import tempfile
# from typing import (
#     TYPE_CHECKING,
#     Any,
#     ClassVar,
#     Tuple,
#     Type,
# )

# from zenml.enums import ArtifactType
# from zenml.io import fileio
# from zenml.materializers.base_materializer import BaseMaterializer

# if TYPE_CHECKING and sys.version_info < (3, 8):
#     BaseIndex = Any
# else:
#     from llama_index.core.indices.base import BaseIndex


# class LlamaIndexIndexMaterializer(BaseMaterializer):
#     """Materializer for llama_index indices."""

#     ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
#     ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (BaseIndex,)

#     def load(self, data_type: Any) -> Any:
#         """Loads a llama-index index from disk.

#         Args:
#             data_type: The type of the index.

#         Returns:
#             The index.
#         """
#         from llama_index.core import StorageContext, load_index_from_storage

#         with tempfile.TemporaryDirectory() as tempdir:
#             fileio.copy_directory(self.uri, tempdir)
#             storage_context = StorageContext.from_defaults(persist_dir=tempdir)

#         return load_index_from_storage(storage_context=storage_context)

#     def save(self, index: Any) -> None:
#         """Save a llama-index index to disk.

#         Args:
#             index: The index to save.
#         """
#         with tempfile.TemporaryDirectory() as tempdir:
#             index.storage_context.persist(persist_dir=tempdir)
#             fileio.copy_directory(tempdir, self.uri)
