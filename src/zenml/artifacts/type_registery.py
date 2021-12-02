#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import TYPE_CHECKING, Dict, List, Type

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact


class ArtifactTypeRegistry(object):
    def __init__(self) -> None:
        self._artifact_types: Dict[str, List[Type["BaseArtifact"]]] = {}

    def register_integration(
        self, key: str, type_: List[Type["BaseArtifact"]]
    ) -> None:
        self._artifact_types[key] = type_

    def get_artifact_type(self, key: str) -> List[Type["BaseArtifact"]]:
        return self._artifact_types[key]


type_registry = ArtifactTypeRegistry()
