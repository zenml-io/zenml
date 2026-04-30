#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Materializer for EvaluationResult artifacts."""

import os
from typing import ClassVar, Tuple, Type

from zenml.enums import ArtifactType
from zenml.evaluators.result import EvaluationResult
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DATA_FILENAME = "evaluation_result.json"


class EvaluationResultMaterializer(BaseMaterializer):
    """Persists EvaluationResult as JSON via Pydantic's model_dump_json."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[EvaluationResult], ...]] = (
        EvaluationResult,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[EvaluationResult]) -> EvaluationResult:
        """Read an EvaluationResult from JSON.

        Args:
            data_type: The type to deserialize into (always EvaluationResult).

        Returns:
            The deserialized EvaluationResult.
        """
        path = os.path.join(self.uri, DATA_FILENAME)
        with fileio.open(path, "r") as f:
            return EvaluationResult.model_validate_json(f.read())

    def save(self, data: EvaluationResult) -> None:
        """Serialize an EvaluationResult to JSON.

        Args:
            data: The EvaluationResult to persist.
        """
        path = os.path.join(self.uri, DATA_FILENAME)
        with fileio.open(path, "w") as f:
            f.write(data.model_dump_json())
