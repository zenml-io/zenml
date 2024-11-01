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

import sys
from typing import TYPE_CHECKING, Any, ClassVar, Tuple, Type

from zenml.enums import ArtifactType
from zenml.materializers.cloudpickle_materializer import (
    CloudpickleMaterializer,
)

if TYPE_CHECKING and sys.version_info < (3, 8):
    OpenAIEmbeddings = Any
else:
    from langchain_community.embeddings import (  # type: ignore[import-untyped]
        OpenAIEmbeddings,
    )


class LangchainOpenaiEmbeddingMaterializer(CloudpickleMaterializer):
    """Handle langchain OpenAI embedding objects."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (OpenAIEmbeddings,)
