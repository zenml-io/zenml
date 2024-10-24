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


import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.modal.flavors import ModalStepOperatorSettings
from zenml.integrations.modal.step_operators.modal_step_operator import (
    get_gpu_values,
)


@pytest.mark.parametrize(
    "gpu, gpu_count, expected_result",
    [
        ("", None, None),
        (None, None, None),
        ("", 1, None),
        (None, 1, None),
        ("A100", None, "A100"),
        ("A100", 0, "A100"),
        ("A100", 1, "A100:1"),
        ("A100", 2, "A100:2"),
        ("V100", None, "V100"),
        ("V100", 0, "V100"),
        ("V100", 1, "V100:1"),
        ("V100", 2, "V100:2"),
    ],
)
def test_get_gpu_values(gpu, gpu_count, expected_result):
    settings = ModalStepOperatorSettings(gpu=gpu)
    resource_settings = ResourceSettings(gpu_count=gpu_count)
    result = get_gpu_values(settings, resource_settings)
    assert result == expected_result
