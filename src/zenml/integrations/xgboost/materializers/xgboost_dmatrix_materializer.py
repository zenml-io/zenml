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
from typing import Any, Type

import xgboost as xgb

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "data.binary"


class XgboostDMatrixMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost."""

    ASSOCIATED_TYPES = (xgb.DMatrix,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> xgb.DMatrix:
        """Reads a xgboost.DMatrix binary file and loads it."""
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "rb") as fid:
            matrix = xgb.DMatrix(fid)
        return matrix

    def handle_return(self, matrix: xgb.DMatrix) -> None:
        """Creates a binary serialization for a xgboost.DMatrix object.

        Args:
            matrix: A xgboost.DMatrix object.
        """
        super().handle_return(matrix)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "wb") as fid:
            matrix.save_binary(fid)
