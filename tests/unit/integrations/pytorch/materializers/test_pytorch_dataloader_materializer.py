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
from contextlib import ExitStack as does_not_raise

from torch.utils.data.dataloader import DataLoader
from torch.utils.data.dataset import Dataset

from tests.unit.test_general import _test_materializer
from zenml.integrations.pytorch.materializers.pytorch_dataloader_materializer import (
    PyTorchDataLoaderMaterializer,
)
from zenml.post_execution.pipeline import PipelineRunView


def test_pytorch_dataloader_materializer(clean_client):
    """Tests whether the steps work for the Sklearn materializer."""
    with does_not_raise():
        _test_materializer(
            step_output=DataLoader(Dataset(), batch_size=37, num_workers=7),
            materializer=PyTorchDataLoaderMaterializer,
        )

    last_run = PipelineRunView(clean_client.zen_store.list_runs()[-1])
    test_step = last_run.steps[-1]
    dataloader = test_step.output.read()

    assert isinstance(dataloader, DataLoader)
    assert dataloader.dataset is not None
    assert dataloader.batch_size == 37
    assert dataloader.num_workers == 7
