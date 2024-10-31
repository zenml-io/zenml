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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

import xgboost as xgb

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "data.binary"


class XgboostDMatrixMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost.DMatrix."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (xgb.DMatrix,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> xgb.DMatrix:
        """Reads a xgboost.DMatrix binary file and loads it.

        Args:
            data_type: The datatype which should be read.

        Returns:
            Materialized xgboost matrix.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

            # Copy from artifact store to temporary file
            fileio.copy(filepath, temp_file)
            matrix = xgb.DMatrix(temp_file)

            return matrix

    def save(self, matrix: xgb.DMatrix) -> None:
        """Creates a binary serialization for a xgboost.DMatrix object.

        Args:
            matrix: A xgboost.DMatrix object.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

            with open(temp_file, "wb") as f:
                matrix.save_binary(f)

            fileio.copy(f, filepath)

    def extract_metadata(
        self, dataset: xgb.DMatrix
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Dataset` object.

        Args:
            dataset: The `Dataset` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {"shape": (dataset.num_row(), dataset.num_col())}
