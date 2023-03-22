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
"""Implementation of the Langchain OpenAI embedding materializer."""


import os
import pickle
from typing import Type, cast

from langchain.embeddings import OpenAIEmbeddings

from zenml.enums import ArtifactType
from zenml.exceptions import ValidationError
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils.io_utils import (
    read_file_contents_as_string,
    write_file_contents_as_string,
)
from zenml.utils.materializer_utils import get_python_version

DEFAULT_PICKLE_FILENAME = "embedding.pkl"
DEFAULT_PYTHON_VERSION_FILENAME = "python_version.txt"


class LangchainOpenaiEmbeddingMaterializer(BaseMaterializer):
    """Handle langchain openai embedding objects."""

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL
    ASSOCIATED_TYPES = (OpenAIEmbeddings,)

    def load(self, data_type: Type[OpenAIEmbeddings]) -> OpenAIEmbeddings:
        """Reads a openai embedding from a pickle file.

        Args:
            data_type: The type of the vector store.

        Returns:
            The vector store.

        Raises:
            ValidationError: If the Python version used to materialize the
                embedding is different from the current Python version.
        """
        super().load(data_type)
        python_version_filepath = os.path.join(
            self.uri, DEFAULT_PYTHON_VERSION_FILENAME
        )
        source_python_version = read_file_contents_as_string(
            python_version_filepath
        )
        current_python_version = get_python_version()
        if source_python_version != current_python_version:
            raise ValidationError(
                f"Your `OpenAIEmbedding` was materialized with {source_python_version} "
                f"but you are currently using {current_python_version}. "
                f"Unable to load this pickled file."
            )

        pickle_filepath = os.path.join(self.uri, DEFAULT_PICKLE_FILENAME)
        with fileio.open(pickle_filepath, "rb") as fid:
            embedding = pickle.load(fid)
        return cast(OpenAIEmbeddings, embedding)

    def save(self, embedding: OpenAIEmbeddings) -> None:
        """Save an OpenAI embedding as a pickle file.

        Args:
            embedding: The embedding to save.
        """
        super().save(embedding)

        pickle_filepath = os.path.join(self.uri, DEFAULT_PICKLE_FILENAME)
        with fileio.open(pickle_filepath, "wb") as fid:
            pickle.dump(embedding, fid)

        # save python version for validation on loading
        python_version_filepath = os.path.join(
            self.uri, DEFAULT_PYTHON_VERSION_FILENAME
        )
        current_python_version = get_python_version()
        write_file_contents_as_string(
            python_version_filepath, current_python_version
        )
