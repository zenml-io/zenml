#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from collections import Counter
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
    Union,
)

import numpy as np

from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import DType, MetadataType

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)


NUMPY_FILENAME = "data.npy"

DATA_FILENAME = "data.parquet"
SHAPE_FILENAME = "shape.json"
DATA_VAR = "data_var"

# Check NumPy version for compatibility handling
IS_NUMPY_2 = np.lib.NumpyVersion(np.__version__) >= "2.0.0"

# In NumPy 2.0, np.object_ is deprecated in favor of object
# Let's use the right type based on the NumPy version
NUMPY_OBJECT_TYPE = object if IS_NUMPY_2 else np.object_


def _ensure_dtype_compatibility(arr: "NDArray[Any]") -> "NDArray[Any]":
    """Ensure consistent dtype handling across NumPy versions.

    Args:
        arr: NumPy array to ensure compatible dtype handling

    Returns:
        NumPy array with consistent dtype behavior
    """
    if IS_NUMPY_2:
        return arr  # NumPy 2.0 already preserves precision
    else:
        # For 1.x, explicitly preserve precision when needed
        return arr.astype(arr.dtype, copy=False)


def _create_array(
    data: Any, dtype: Optional[Union["np.dtype[Any]", Type[Any]]] = None
) -> "NDArray[Any]":
    """Create arrays with consistent behavior across NumPy versions.

    Args:
        data: Data to convert to array
        dtype: Optional dtype to use

    Returns:
        NumPy array with consistent creation behavior
    """
    if IS_NUMPY_2:
        return np.asarray(data, dtype=dtype)
    else:
        # In NumPy 1.x, copy behavior is different
        return np.array(data, dtype=dtype, copy=False)


class NumpyMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (np.ndarray,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> "Any":
        """Reads a numpy array from a `.npy` file.

        Args:
            data_type: The type of the data to read.


        Raises:
            ImportError: If pyarrow is not installed.

        Returns:
            The numpy array.
        """
        numpy_file = os.path.join(self.uri, NUMPY_FILENAME)

        if self.artifact_store.exists(numpy_file):
            with self.artifact_store.open(numpy_file, "rb") as f:
                arr = np.load(f, allow_pickle=True)
                # Ensure consistent dtype handling
                return _ensure_dtype_compatibility(arr)
        elif self.artifact_store.exists(os.path.join(self.uri, DATA_FILENAME)):
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
                with self.artifact_store.open(
                    os.path.join(self.uri, DATA_FILENAME), "rb"
                ) as f:
                    input_stream = pa.input_stream(f)
                    data = pq.read_table(input_stream)
                vals = getattr(data.to_pandas(), DATA_VAR).values
                arr = np.reshape(vals, shape_tuple)
                # Ensure consistent dtype handling
                return _ensure_dtype_compatibility(arr)
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
        # Ensure consistent dtype handling before saving
        arr = _ensure_dtype_compatibility(arr)

        with self.artifact_store.open(
            os.path.join(self.uri, NUMPY_FILENAME), "wb"
        ) as f:
            np.save(f, arr)

    def save_visualizations(
        self, arr: "NDArray[Any]"
    ) -> Dict[str, VisualizationType]:
        """Saves visualizations for a numpy array.

        If the array is 1D, a histogram is saved. If the array is 2D or 3D with
        3 or 4 channels, an image is saved.

        Args:
            arr: The numpy array to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        if not np.issubdtype(arr.dtype, np.number):
            return {}

        try:
            # Save histogram for 1D arrays
            if len(arr.shape) == 1:
                histogram_path = os.path.join(self.uri, "histogram.png")
                histogram_path = histogram_path.replace("\\", "/")
                self._save_histogram(histogram_path, arr)
                return {histogram_path: VisualizationType.IMAGE}

            # Save as image for 3D arrays with 3 or 4 channels
            if len(arr.shape) == 3 and arr.shape[2] in [3, 4]:
                image_path = os.path.join(self.uri, "image.png")
                image_path = image_path.replace("\\", "/")
                self._save_image(image_path, arr)
                return {image_path: VisualizationType.IMAGE}

        except ImportError:
            logger.info(
                "Skipping visualization of numpy array because matplotlib "
                "is not installed. To install matplotlib, run "
                "`pip install matplotlib`."
            )

        return {}

    def _save_histogram(self, output_path: str, arr: "NDArray[Any]") -> None:
        """Saves a histogram of a numpy array.

        Args:
            output_path: The path to save the histogram to.
            arr: The numpy array of which to save the histogram.
        """
        import matplotlib.pyplot as plt

        plt.hist(arr)
        with self.artifact_store.open(output_path, "wb") as f:
            plt.savefig(f)
        plt.close()

    def _save_image(self, output_path: str, arr: "NDArray[Any]") -> None:
        """Saves a numpy array as an image.

        Args:
            output_path: The path to save the image to.
            arr: The numpy array to save.
        """
        from matplotlib.image import imsave

        with self.artifact_store.open(output_path, "wb") as f:
            imsave(f, arr)

    def extract_metadata(
        self, arr: "NDArray[Any]"
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given numpy array.

        Args:
            arr: The numpy array to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        if np.issubdtype(arr.dtype, np.number):
            return self._extract_numeric_metadata(arr)
        elif np.issubdtype(arr.dtype, np.str_) or np.issubdtype(
            arr.dtype, NUMPY_OBJECT_TYPE
        ):
            return self._extract_text_metadata(arr)
        else:
            return {}

    def _extract_numeric_metadata(
        self, arr: "NDArray[Any]"
    ) -> Dict[str, "MetadataType"]:
        """Extracts numeric metadata from a numpy array.

        Args:
            arr: The numpy array to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        # Ensure consistent precision handling
        arr = _ensure_dtype_compatibility(arr)

        min_val = np.min(arr).item()
        max_val = np.max(arr).item()

        numpy_metadata: Dict[str, "MetadataType"] = {
            "shape": tuple(arr.shape),
            "dtype": DType(arr.dtype.type),
            "mean": np.mean(arr).item(),
            "std": np.std(arr).item(),
            "min": min_val,
            "max": max_val,
        }
        return numpy_metadata

    def _extract_text_metadata(
        self, arr: "NDArray[Any]"
    ) -> Dict[str, "MetadataType"]:
        """Extracts text metadata from a numpy array.

        Args:
            arr: The numpy array to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        # Convert all array elements to strings explicitly to handle
        # mixed types and ensure NumPy 2.0 compatibility
        str_items = [str(item) for item in arr.flat]
        # Use dtype='U' (unicode string) instead of str to avoid type issues
        str_arr = _create_array(str_items, dtype=np.dtype("U")).reshape(
            arr.shape
        )

        text = " ".join(str_arr)
        words = text.split()
        word_counts = Counter(words)
        unique_words = len(word_counts)
        total_words = len(words)
        most_common_word, most_common_count = word_counts.most_common(1)[0]

        text_metadata: Dict[str, "MetadataType"] = {
            "shape": tuple(arr.shape),
            "dtype": DType(arr.dtype.type),
            "unique_words": unique_words,
            "total_words": total_words,
            "most_common_word": most_common_word,
            "most_common_count": most_common_count,
        }
        return text_metadata
