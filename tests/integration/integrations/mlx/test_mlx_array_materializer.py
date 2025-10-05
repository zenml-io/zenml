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

import sys

import mlx.core as mx
import pytest

from tests.unit.test_general import _test_materializer
from zenml.integrations.mlx import SUPPORTED_PLATFORMS
from zenml.integrations.mlx.materializer import MLXArrayMaterializer


@pytest.mark.skipif(
    sys.platform not in SUPPORTED_PLATFORMS,
    reason="MLX only runs on Apple and Linux",
)
def test_mlx_array_materializer():
    """Test the MLX array materializer."""
    arr = mx.ones(5)

    result = _test_materializer(
        step_output_type=mx.array,
        materializer_class=MLXArrayMaterializer,
        step_output=arr,
    )
    assert mx.allclose(arr, result).item()
