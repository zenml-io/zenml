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
"""Implementation of the Scipy Sparse Materializer."""

import os
from typing import Any, Type

from scipy.sparse import load_npz, save_npz, spmatrix

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DATA_FILENAME = "data.npz"


class SparseMaterializer(BaseMaterializer):
    """Materializer to read and write scipy sparse matrices."""

    ASSOCIATED_TYPES = (spmatrix,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> spmatrix:
        """Reads spmatrix from npz file.

        Args:
            data_type: The type of the spmatrix to load.

        Returns:
            A spmatrix object.
        """
        super().load(data_type)
        with fileio.open(os.path.join(self.uri, DATA_FILENAME), "rb") as f:
            mat = load_npz(f)
        return mat

    def save(self, mat: spmatrix) -> None:
        """Writes a spmatrix to the artifact store as a npz file.

        Args:
            mat: The spmatrix to write.
        """
        super().save(mat)
        with fileio.open(os.path.join(self.uri, DATA_FILENAME), "wb") as f:
            save_npz(f, mat)
