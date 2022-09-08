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

from zenml.integrations.pytorch.materializers.pytorch_dataloader_materializer import (
    PyTorchDataLoaderMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step


def test_pytorch_module_materializer(clean_repo):
    """Tests whether the steps work for the Sklearn materializer."""

    @step
    def read_dataloader() -> DataLoader:
        """Reads and materializes a PyTorch DataLoader."""
        return DataLoader(Dataset(), batch_size=37, num_workers=7)

    @pipeline
    def test_pipeline(read_dataloader) -> None:
        """Tests the PyTorch DataLoader materializer."""
        read_dataloader()

    with does_not_raise():
        test_pipeline(
            read_dataloader=read_dataloader().with_return_materializers(
                PyTorchDataLoaderMaterializer
            )
        ).run()

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    dataloader = last_run.steps[-1].output.read()
    assert isinstance(dataloader, DataLoader)
    assert dataloader.dataset is not None
    assert dataloader.batch_size == 37
    assert dataloader.num_workers == 7
