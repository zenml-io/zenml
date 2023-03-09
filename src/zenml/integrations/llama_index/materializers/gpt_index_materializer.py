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


import os
from typing import Type

from llama_index.indices.base import BaseGPTIndex
from llama_index.indices.vector_store import GPTFaissIndex

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "index.json"
DEFAULT_FAISS_FILENAME = "faiss_index.json"


class LlamaIndexGPTIndexMaterializer(BaseMaterializer):

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL
    ASSOCIATED_TYPES = (BaseGPTIndex,)

    def load(self, data_type: Type[BaseGPTIndex]) -> BaseGPTIndex:
        """Loads a llama-index GPT index from disk.

        Args:
            data_type: The type of the index.

        Returns:
            The index.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        return data_type.load_from_disk(save_path=filepath)

    def save(self, index: BaseGPTIndex) -> None:
        """Save a llama-index GPT index to disk.

        Args:
            index: The index to save.
        """
        super().save(index)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        index.save_to_disk(save_path=filepath)


class LlamaIndexGPTFaissIndexMaterializer(BaseMaterializer):

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL
    ASSOCIATED_TYPES = (GPTFaissIndex,)

    def load(self, data_type: Type[GPTFaissIndex]) -> GPTFaissIndex:
        """Loads a llama-index GPT faiss index from disk.

        Args:
            data_type: The type of the index.

        Returns:
            The index.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        faiss_filepath = os.path.join(self.uri, DEFAULT_FAISS_FILENAME)
        return data_type.load_from_disk(
            save_path=filepath, faiss_index_save_path=faiss_filepath
        )

    def save(self, index: GPTFaissIndex) -> None:
        """Save a llama-index GPT faiss index to disk.

        Args:
            index: The index to save.
        """
        super().save(index)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        faiss_filepath = os.path.join(self.uri, DEFAULT_FAISS_FILENAME)
        index.save_to_disk(
            save_path=filepath, faiss_index_save_path=faiss_filepath
        )
