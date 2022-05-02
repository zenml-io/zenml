#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os
import tempfile
from typing import Any, Type

from deepchecks.core import SuiteResult, CheckResult
from zenml.artifacts import DataAnalysisArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.txt"


class DeepchecksResultMaterializer(BaseMaterializer):
    """Materializer to read data to and from lightgbm.Booster."""

    ASSOCIATED_TYPES = (CheckResult,)
    ASSOCIATED_ARTIFACT_TYPES = (DataAnalysisArtifact,)

    def handle_input(self, data_type: Type[Any]) -> CheckResult:
        """Reads a lightgbm Booster model from a serialized JSON file."""
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        booster = CheckResult(model_file=temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)
        return booster

    def handle_return(self, result: SuiteResult) -> None:
        """Creates a JSON serialization for a lightgbm Booster model.

        Args:
            result: A lightgbm Booster model.
        """
        super().handle_return(result)

        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)

        result.to_json(False)

        # Make a temporary phantom artifact
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=True
        ) as f:
            booster.save_model(f.name)
            # Copy it into artifact store
            fileio.copy(f.name, filepath)
