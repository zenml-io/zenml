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
"""Implementation of the XGBoost dmatrix materializer."""

import os
import tempfile
from typing import Any, Type

import xgboost as xgb

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "data.binary"


class XgboostDMatrixMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost.DMatrix."""

    ASSOCIATED_TYPES = (xgb.DMatrix,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> xgb.DMatrix:
        """Reads a xgboost.DMatrix binary file and loads it.

        Args:
            data_type: The datatype which should be read.

        Returns:
            Materialized xgboost matrix.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        matrix = xgb.DMatrix(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)
        return matrix

    def save(self, matrix: xgb.DMatrix) -> None:
        """Creates a binary serialization for a xgboost.DMatrix object.

        Args:
            matrix: A xgboost.DMatrix object.
        """
        super().save(matrix)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Make a temporary phantom artifact
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            matrix.save_binary(f.name)
            # Copy it into artifact store
            fileio.copy(f.name, filepath)

        # Close and remove the temporary file
        f.close()
        fileio.remove(f.name)
