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
"""Implementation of the ZenML NumPy materializer."""

import os
from typing import TYPE_CHECKING, Any, Type

import numpy as np

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

if TYPE_CHECKING:
    from numpy.typing import NDArray

NUMPY_FILENAME = "data.npy"


class NumpyMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (np.ndarray,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> "Any":
        """Reads numpy array from npy file.

        Args:
            data_type: The type of the data to read.

        Returns:
            The numpy array.
        """
        super().handle_input(data_type)
        with fileio.open(
            os.path.join(self.artifact.uri, NUMPY_FILENAME), "rb"
        ) as f:
            return np.load(f, allow_pickle=True)  # type: ignore

    def handle_return(self, arr: "NDArray[Any]") -> None:
        """Writes a np.ndarray to the artifact store as a npy file.

        Args:
            arr: The numpy array to write.
        """
        super().handle_return(arr)
        with fileio.open(
            os.path.join(self.artifact.uri, NUMPY_FILENAME), "wb"
        ) as f:
            np.save(f, arr)  # type: ignore
