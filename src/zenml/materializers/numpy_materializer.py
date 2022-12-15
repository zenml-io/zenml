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
from typing import TYPE_CHECKING, Any, Type, cast

import numpy as np

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)


NUMPY_FILENAME = "data.npy"

DATA_FILENAME = "data.parquet"
SHAPE_FILENAME = "shape.json"
DATA_VAR = "data_var"


class NumpyMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (np.ndarray,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> "Any":
        """Reads a numpy array from a `.npy` file.

        Args:
            data_type: The type of the data to read.


        Raises:
            ImportError: If pyarrow is not installed.

        Returns:
            The numpy array.
        """
        super().load(data_type)

        numpy_file = os.path.join(self.uri, NUMPY_FILENAME)

        if fileio.exists(numpy_file):
            with fileio.open(numpy_file, "rb") as f:
                # This function is untyped for numpy versions supporting python
                # 3.7, but typed for numpy versions installed on python 3.8+.
                # We need to cast it to any here so that numpy doesn't complain
                # about either an untyped function call or an unused ignore
                # statement
                return cast(Any, np.load)(f, allow_pickle=True)
        elif fileio.exists(os.path.join(self.uri, DATA_FILENAME)):
            logger.warning(
                "A legacy artifact was found. "
                "This artifact was created with an older version of "
                "ZenML. You can still use it, but it will be "
                "converted to the new format on the next materialization."
            )
            try:
                # Import old materializer dependencies
                import pyarrow as pa  # type: ignore
                import pyarrow.parquet as pq  # type: ignore

                from zenml.utils import yaml_utils

                # Read numpy array from parquet file
                shape_dict = yaml_utils.read_json(
                    os.path.join(self.uri, SHAPE_FILENAME)
                )
                shape_tuple = tuple(shape_dict.values())
                with fileio.open(
                    os.path.join(self.uri, DATA_FILENAME), "rb"
                ) as f:
                    input_stream = pa.input_stream(f)
                    data = pq.read_table(input_stream)
                vals = getattr(data.to_pandas(), DATA_VAR).values
                return np.reshape(vals, shape_tuple)
            except ImportError:
                raise ImportError(
                    "You have an old version of a `NumpyMaterializer` ",
                    "data artifact stored in the artifact store ",
                    "as a `.parquet` file, which requires `pyarrow` for reading. ",
                    "You can install `pyarrow` by running `pip install pyarrow`.",
                )

    def save(self, arr: "NDArray[Any]") -> None:
        """Writes a np.ndarray to the artifact store as a `.npy` file.

        Args:
            arr: The numpy array to write.
        """
        super().save(arr)
        with fileio.open(os.path.join(self.uri, NUMPY_FILENAME), "wb") as f:
            # This function is untyped for numpy versions supporting python
            # 3.7, but typed for numpy versions installed on python 3.8+.
            # We need to cast it to any here so that numpy doesn't complain
            # about either an untyped function call or an unused ignore
            # statement
            cast(Any, np.save)(f, arr)
