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
"""Implementation of the PyTorch Lightning Materializer."""

import os
from typing import Any, Type, cast

import torch
from torch.nn import Module

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

CHECKPOINT_NAME = "final_checkpoint.ckpt"


class PyTorchLightningMaterializer(BaseMaterializer):
    """Materializer to read/write PyTorch models."""

    ASSOCIATED_TYPES = (Module,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> Module:
        """Reads and returns a PyTorch Lightning model.

        Args:
            data_type: The type of the model to load.

        Returns:
            A PyTorch Lightning model object.
        """
        super().load(data_type)
        with fileio.open(os.path.join(self.uri, CHECKPOINT_NAME), "rb") as f:
            return cast(Module, torch.load(f))

    def save(self, model: Module) -> None:
        """Writes a PyTorch Lightning model.

        Args:
            model: The PyTorch Lightning model to save.
        """
        super().save(model)
        with fileio.open(os.path.join(self.uri, CHECKPOINT_NAME), "wb") as f:
            torch.save(model, f)
