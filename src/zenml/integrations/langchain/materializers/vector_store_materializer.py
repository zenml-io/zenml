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
"""Implementation of the langchain vector store materializer."""

from typing import Any, ClassVar, Tuple, Type

from langchain.vectorstores.base import VectorStore

from zenml.enums import ArtifactType
from zenml.materializers.cloudpickle_materializer import (
    CloudpickleMaterializer,
)


class LangchainVectorStoreMaterializer(CloudpickleMaterializer):
    """Handle langchain vector store objects."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (VectorStore,)
