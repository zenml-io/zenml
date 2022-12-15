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
"""Implementation of the PyTorch DataLoader materializer."""

import os
from typing import Any, Type

import torch
from torch.utils.data.dataloader import DataLoader

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "entire_dataloader.pt"
CHECKPOINT_FILENAME = "checkpoint.pt"


class PyTorchDataLoaderMaterializer(BaseMaterializer):
    """Materializer to read/write PyTorch dataloaders."""

    ASSOCIATED_TYPES = (DataLoader,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[Any]) -> Any:
        """Reads and returns a PyTorch dataloader.

        Args:
            data_type: The type of the dataloader to load.

        Returns:
            A loaded PyTorch dataloader.
        """
        super().load(data_type)
        with fileio.open(os.path.join(self.uri, DEFAULT_FILENAME), "rb") as f:
            return torch.load(f)

    def save(self, dataloader: Any) -> None:
        """Writes a PyTorch dataloader.

        Args:
            dataloader: A torch.utils.DataLoader or a dict to pass into dataloader.save
        """
        super().save(dataloader)

        # Save entire dataloader to artifact directory
        with fileio.open(os.path.join(self.uri, DEFAULT_FILENAME), "wb") as f:
            torch.save(dataloader, f)
