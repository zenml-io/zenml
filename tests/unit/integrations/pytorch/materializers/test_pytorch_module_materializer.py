#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from torch.nn import Linear

from tests.unit.test_general import _test_materializer
from zenml.integrations.pytorch.materializers.pytorch_module_materializer import (
    PyTorchModuleMaterializer,
)


def test_pytorch_module_materializer(clean_workspace):
    """Tests whether the steps work for the Sklearn materializer."""
    module = _test_materializer(
        step_output=Linear(20, 20),
        materializer_class=PyTorchModuleMaterializer,
        expected_metadata_size=3,
    )

    assert module.in_features == 20
    assert module.out_features == 20
    assert module.bias is not None
