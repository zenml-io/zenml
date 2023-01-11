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
"""Implementation of the LightGBM materializer."""

import os
import tempfile
from typing import Any, Type

import lightgbm as lgb

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "data.binary"


class LightGBMDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from lightgbm.Dataset."""

    ASSOCIATED_TYPES = (lgb.Dataset,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> lgb.Dataset:
        """Reads a lightgbm.Dataset binary file and loads it.

        Args:
            data_type: A lightgbm.Dataset type.

        Returns:
            A lightgbm.Dataset object.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        matrix = lgb.Dataset(temp_file, free_raw_data=False)

        # No clean up this time because matrix is lazy loaded
        return matrix

    def save(self, matrix: lgb.Dataset) -> None:
        """Creates a binary serialization for a lightgbm.Dataset object.

        Args:
            matrix: A lightgbm.Dataset object.
        """
        super().save(matrix)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Make a temporary phantom artifact
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)
        matrix.save_binary(temp_file)

        # Copy it into artifact store
        fileio.copy(temp_file, filepath)
        fileio.rmtree(temp_dir)
