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


def test_object_array_handling():
    """Test that arrays with Python objects are handled correctly.

    This ensures our materializer works with object arrays on any NumPy version.
    """
    # Create an array with Python objects
    object_array = np.array(
        [{"key": "value"}, ["list", "items"], (1, 2, 3)], dtype=object
    )

    # Test serialization and deserialization
    result, metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=object_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Verify the array was properly handled
    assert len(result) == 3
    assert isinstance(result[0], dict)
    assert isinstance(result[1], list)
    assert isinstance(result[2], tuple)

    # Verify structure is preserved
    assert result[0]["key"] == "value"
    assert result[1][0] == "list"
    assert result[2][2] == 3

    # Verify metadata
    assert metadata["shape"] == (3,)


def test_numpy2_compatibility():
    """Test NumPy 2.0 compatibility issues.

    Tests:
    1. Data type promotion changes with explicit casting
    2. Default integer type changes
    3. Mixed type text arrays
    """
    # Test data type promotion with floating point values
    float_array = np.array([1.0, 2.5, 3.7])
    float_result, float_metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=float_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Verify preservation of float values
    assert np.array_equal(float_array, float_result)
    assert float_metadata["mean"] == float_array.mean()

    # Test explicit integer arrays (64-bit)
    int64_array = np.array([1, 2, 3], dtype=np.int64)
    int64_result, int64_metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=int64_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Verify proper handling of int64 values
    assert np.array_equal(int64_array, int64_result)
    assert int64_result.dtype == np.int64

    # Test mixed type text arrays that include numbers
    mixed_array = np.array(["text", 123, 45.67, True, None, {"key": "value"}])
    mixed_result, mixed_metadata = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=mixed_array,
        return_metadata=True,
        expected_metadata_size=7,
    )

    # Verify string extraction works with mixed types
    assert mixed_metadata["total_words"] > 0
    assert "unique_words" in mixed_metadata
    assert "most_common_word" in mixed_metadata

    # Ensure proper serialization and deserialization
    assert len(mixed_result) == len(mixed_array)
    # Check that types are maintained for object arrays
    if mixed_array.dtype == np.dtype("O"):
        assert isinstance(mixed_result[0], str)
        assert isinstance(mixed_result[1], int) or isinstance(
            mixed_result[1], np.integer
        )
        assert isinstance(mixed_result[2], float) or isinstance(
            mixed_result[2], np.floating
        )


def test_integer_type_handling():
    """Test explicit integer type handling for NumPy 2.0 compatibility.

    In NumPy 2.0, the default integer is 64-bit on all 64-bit systems.
    This test ensures that integer arrays with specific dtypes are
    handled correctly.
    """
    # Test various integer types
    int_types = [
        np.int8,
        np.int16,
        np.int32,
        np.int64,
        np.uint8,
        np.uint16,
        np.uint32,
        np.uint64,
    ]

    for int_type in int_types:
        # Create an array with the specific integer type
        test_array = np.array([1, 2, 3], dtype=int_type)

        # Serialize and deserialize
        result, metadata = _test_materializer(
            step_output_type=np.ndarray,
            materializer_class=NumpyMaterializer,
            step_output=test_array,
            return_metadata=True,
            expected_metadata_size=7,
        )

        # Verify the dtype is preserved
        assert result.dtype == test_array.dtype, (
            f"Failed to preserve dtype {int_type}"
        )

        # Verify metadata correctly identifies the type
        assert metadata["dtype"] == DType(test_array.dtype.type)

        # Verify values are preserved accurately
        assert np.array_equal(result, test_array)
