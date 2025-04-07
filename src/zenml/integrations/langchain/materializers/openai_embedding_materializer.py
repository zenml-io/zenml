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

from typing import Any, ClassVar, Tuple, Type

from langchain_community.embeddings import (
    OpenAIEmbeddings,
)

from zenml.enums import ArtifactType
from zenml.materializers.cloudpickle_materializer import (
    CloudpickleMaterializer,
)


class LangchainOpenaiEmbeddingMaterializer(CloudpickleMaterializer):
    """Materializer for Langchain OpenAI Embeddings."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (OpenAIEmbeddings,)

    def save(self, embeddings: Any) -> None:
        """Saves the embeddings model after clearing non-picklable clients.

        Args:
            embeddings: The embeddings model to save.
        """
        # Clear the clients which will be recreated on load
        embeddings.client = None
        embeddings.async_client = None

        # Use the parent class's save implementation which uses cloudpickle
        super().save(embeddings)

    def load(self, data_type: Type[Any]) -> Any:
        """Loads the embeddings model and lets it recreate clients when needed.

        Args:
            data_type: The type of the data to load.

        Returns:
            The loaded embeddings model.
        """
        return super().load(data_type)
