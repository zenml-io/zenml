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
from tempfile import TemporaryDirectory
from typing import Dict

import numpy as np

from tests.unit.test_general import _test_materializer
from zenml.materializers.numpy_materializer import NumpyMaterializer
from zenml.metadata.metadata_types import (
    DType,
    MetadataType,
    MetadataTypeTuple,
)


def test_numpy_materializer():
    """Test the numpy materializer."""
    arr = np.array([0, 1, 2, "hello", "world", "hello"])

    result = _test_materializer(
        step_output_type=np.ndarray,
        materializer_class=NumpyMaterializer,
        step_output=arr,
    )
    assert np.array_equal(arr, result)


def test_extract_metadata():
    """Test the extract_metadata method of the NumpyMaterializer."""

    def _test_extract_metadata(
        step_output: np.ndarray,
    ) -> Dict[str, MetadataType]:
        with TemporaryDirectory() as artifact_uri:
            materializer = NumpyMaterializer(uri=artifact_uri)
            existing_files = os.listdir(artifact_uri)

            # Assert that materializer saves something to disk
            materializer.save(step_output)
            new_files = os.listdir(artifact_uri)
            assert len(new_files) > len(
                existing_files
            )  # something was written

            # Assert that metadata extraction returns a dict
            metadata = materializer.extract_metadata(step_output)
            assert isinstance(metadata, dict)
            for key, value in metadata.items():
                assert isinstance(key, str)
                assert isinstance(value, MetadataTypeTuple)

            return metadata

    numeric_array = np.array(
        [
            1,
            2,
            3,
        ]
    )
    numeric_metadata = _test_extract_metadata(numeric_array)
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
    text_metadata = _test_extract_metadata(text_array)

    # Assert that the extracted metadata is correct for text array
    assert text_metadata["dtype"] == DType(text_array.dtype.type)
    assert text_metadata["shape"] == (7,)
    assert text_metadata["unique_words"] == 6
    assert text_metadata["total_words"] == 7
    assert text_metadata["most_common_word"] == "world"
    assert text_metadata["most_common_count"] == 2
