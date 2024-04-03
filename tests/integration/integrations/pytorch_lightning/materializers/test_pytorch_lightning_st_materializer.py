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

from tests.unit.test_general import _test_materializer
from torch.nn import Linear

from zenml.integrations.pytorch_lightning.materializers.pytorch_lightning_st_materializer import (
    PyTorchLightningSTMaterializer,
)


def test_pytorch_lightning_materializer(clean_client):
    """Tests whether the steps work for the PyTorch Lightning materializer using safetensors."""
    module = _test_materializer(
        step_output=Linear(20, 20),
        materializer_class=PyTorchLightningSTMaterializer,
        expected_metadata_size=1,
    )

    assert module.in_features == 20
    assert module.out_features == 20
    assert module.bias is not None
