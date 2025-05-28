#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import importlib
import os
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Optional,
    Tuple,
    Type,
    Union,
)

# TODO: Make the following two imports optional.
import jax
import mlx.core as mx
import numpy as np

from zenml.enums import ArtifactType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)

NUMPY_FILENAME = "data.npy"


def _create_array(
    data: Any,
    namespace: str,
    dtype: Optional[Union["np.dtype[Any]", Type[Any]]] = None,
) -> "NDArray[Any]":
    """Create abstract arrays from data together with an array namespace specifier.

    Args:
        data: Data to convert to array.
        namespace: Array namespace to look up.
        dtype: Optional dtype to use.

    Returns:
        An abstract array.
    """
    # Normally, we would access the data's __array_namespace__, but data in this context
    # is either not yet array-like, or it's just a NumPy array returned from np.load() in the
    # materializer's load() method, so we look up the namespace via importlib instead.
    # The namespace name is given by the requested data type in the materializer's load() method.
    namespace = importlib.import_module(namespace)
    # TODO: Handle dict case of np.load
    return namespace.asarray(data, dtype=dtype)


class ArrayMaterializer(BaseMaterializer):
    """Materializer for array libraries conforming to the Python Array API standard.

    This includes, but is not limited to NumPy, JAX, cupy, and MLX.
    For more information, see https://data-apis.org/array-api/latest/index.html.
    """

    # TODO: How to reference associated types without having to install all of them?
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
        np.ndarray,
        jax.Array,
        mx.array,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> "Any":
        """Reads data from a `.npy` file, and returns an abstract array.

        Args:
            data_type: The type of the data to read.

        Returns:
            The abstract array.
        """
        logger.debug(
            f"Array type {data_type!r} processed by {self.__class__.__name__}"
        )
        numpy_file = os.path.join(self.uri, NUMPY_FILENAME)

        if self.artifact_store.exists(numpy_file):
            with self.artifact_store.open(numpy_file, "rb") as f:
                arr = np.load(f, allow_pickle=True)
                # TODO: Make this dynamic.
                if data_type is np.ndarray:
                    namespace = "numpy"
                elif data_type is jax.Array:
                    namespace = "jax.numpy"
                elif data_type is mx.array:
                    namespace = "mlx.core"
                else:
                    raise ValueError(f"non-array datatype: {data_type!r}")
                return _create_array(arr, namespace=namespace)

    # TODO: Improve this type annotation
    def save(self, arr: "NDArray[Any]") -> None:
        """Writes an abstract array to the artifact store as a `.npy` file.

        Args:
            arr: The abstract array to write.
        """
        with self.artifact_store.open(
            os.path.join(self.uri, NUMPY_FILENAME), "wb"
        ) as f:
            np.save(f, arr)
