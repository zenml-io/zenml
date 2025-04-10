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

import numpy as np

from tests.unit.test_general import _test_materializer
from zenml.integrations.numpy.materializers.numpy_materializer import (
    IS_NUMPY_2,
    NUMPY_OBJECT_TYPE,
    NumpyMaterializer,
)
from zenml.metadata.metadata_types import (
    DType,
)


def test_numpy_materializer():
    """Test the numpy materializer with metadata extraction."""

    numeric_array = np.array(
        [
            1,
            2,
            3,
        ]
    )

    # Test the materializer with metadata extraction
    numeric_result, numeric_metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=numeric_array,
        return_metadata=True,
        expected_metadata_size=7,
        assert_visualization_exists=True,
    )

    # Assert that the materialized array is correct
    assert np.array_equal(numeric_array, numeric_result)

    # Assert that the extracted metadata is correct for numeric array
    assert numeric_metadata["shape"] == (3,)
    assert numeric_metadata["dtype"] == DType(numeric_array.dtype.type)
    assert numeric_metadata["mean"] == 2.0
    assert numeric_metadata["std"] == 0.816496580927726
    assert numeric_metadata["min"] == 1
    assert numeric_metadata["max"] == 3

    text_array = np.array(
        [
            "Hello",
            "world",
            "hello",
            "zenml",
            "world",
            0.35,
            1,
        ]
    )

    # Test the materializer with metadata extraction
    text_result, text_metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=text_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Assert that the materialized array is correct
    assert np.array_equal(text_array, text_result)

    # Assert that the extracted metadata is correct for text array
    assert text_metadata["dtype"] == DType(text_array.dtype.type)
    assert text_metadata["shape"] == (7,)
    assert text_metadata["unique_words"] == 6
    assert text_metadata["total_words"] == 7
    assert text_metadata["most_common_word"] == "world"
    assert text_metadata["most_common_count"] == 2


def test_numpy_version_compatibility():
    """Test NumPy version compatibility handling in the materializer."""
    # Create an array with Python objects - this tests our NUMPY_OBJECT_TYPE handling
    object_array = np.array(
        [{"key": "value"}, ["list", "items"], (1, 2, 3)], dtype=object
    )

    # Test the materializer with the object array
    result, metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=object_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Verify the array was properly handled
    assert np.array_equal(object_array, result)
    assert metadata["shape"] == (3,)

    # Verify our version detection logic is consistent
    # In NumPy 2.x, np.object_ is object
    if IS_NUMPY_2:
        assert NUMPY_OBJECT_TYPE is object
        # Print version info for test log clarity
        print(f"Running with NumPy 2.x: {np.__version__}")
    else:
        assert NUMPY_OBJECT_TYPE is np.object_
        # Print version info for test log clarity
        print(f"Running with NumPy 1.x: {np.__version__}")

    # Make sure dtype detection works correctly regardless of version
    assert np.issubdtype(object_array.dtype, NUMPY_OBJECT_TYPE)
