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
import sys
from typing import TYPE_CHECKING, Any, Type, cast

import pkg_resources

from zenml.enums import ArtifactType
from zenml.environment import Environment
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils.io_utils import (
    read_file_contents_as_string,
    write_file_contents_as_string,
)

if TYPE_CHECKING and sys.version_info < (3, 8):
    OpenAIEmbeddings = Any
else:
    from langchain.embeddings import OpenAIEmbeddings

DEFAULT_PICKLE_FILENAME = "embedding.pkl"
DEFAULT_PYTHON_VERSION_FILENAME = "python_version.txt"
DEFAULT_LANGCHAIN_VERSION_FILENAME = "langchain_version.txt"
LANGCHAIN_PACKAGE_NAME = "langchain"

logger = get_logger(__name__)


class LangchainOpenaiEmbeddingMaterializer(BaseMaterializer):
    """Handle langchain openai embedding objects."""

    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL
    ASSOCIATED_TYPES = (OpenAIEmbeddings,)

    def load(self, data_type: Type[OpenAIEmbeddings]) -> OpenAIEmbeddings:
        """Reads an OpenAI embedding from a pickle file.

        Args:
            data_type: The type of the vector store.

        Returns:
            The vector store.
        """
        super().load(data_type)

        # validate langchain package version
        langchain_version_filepath = os.path.join(
            self.uri, DEFAULT_LANGCHAIN_VERSION_FILENAME
        )
        source_langchain_version = read_file_contents_as_string(
            langchain_version_filepath
        )
        try:
            package_version = pkg_resources.get_distribution(
                LANGCHAIN_PACKAGE_NAME
            ).version
        except pkg_resources.DistributionNotFound:
            logger.warn(
                f"'{LANGCHAIN_PACKAGE_NAME}' package is not installed."
            )
            package_version = "not installed"
        if source_langchain_version != package_version:
            logger.warn(
                f"Your `OpenAIEmbedding` was materialized with {source_langchain_version} "
                f"but you are currently using {package_version}. "
                f"This might cause unexpected behavior. Attempting to load."
            )

        # validate python version
        python_version_filepath = os.path.join(
            self.uri, DEFAULT_PYTHON_VERSION_FILENAME
        )
        source_python_version = read_file_contents_as_string(
            python_version_filepath
        )
        current_python_version = Environment().python_version()
        if source_python_version != current_python_version:
            logger.warn(
                f"Your `OpenAIEmbedding` was materialized with {source_python_version} "
                f"but you are currently using {current_python_version}. "
                f"This might cause unexpected behavior. Attempting to load."
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
        current_python_version = Environment().python_version()
        write_file_contents_as_string(
            python_version_filepath, current_python_version
        )

        # save langchain package version foa
        try:
            package_version = pkg_resources.get_distribution(
                LANGCHAIN_PACKAGE_NAME
            ).version
        except pkg_resources.DistributionNotFound:
            logger.warn(
                f"'{LANGCHAIN_PACKAGE_NAME}' package is not installed."
            )
            package_version = "not installed"
        langchain_version_filepath = os.path.join(
            self.uri, DEFAULT_LANGCHAIN_VERSION_FILENAME
        )
        write_file_contents_as_string(
            langchain_version_filepath, package_version
        )
