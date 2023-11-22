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

import torch
from torch.utils.data.dataloader import DataLoader
from torch.utils.data.dataset import TensorDataset

from tests.unit.test_general import _test_materializer
from zenml.integrations.pytorch.materializers.pytorch_dataloader_materializer import (
    PyTorchDataLoaderMaterializer,
)


def test_pytorch_dataloader_materializer(clean_client):
    """Tests whether the steps work for the Sklearn materializer."""
    dataset = TensorDataset(torch.tensor([1, 2, 3, 4, 5]))
    dataloader = _test_materializer(
        step_output=DataLoader(dataset, batch_size=3, num_workers=7),
        materializer_class=PyTorchDataLoaderMaterializer,
        expected_metadata_size=4,
    )

    assert dataloader.dataset is not None
    assert len(dataloader.dataset) == 5
    assert dataloader.batch_size == 3
    assert len(dataloader) == 2
    assert dataloader.num_workers == 7
