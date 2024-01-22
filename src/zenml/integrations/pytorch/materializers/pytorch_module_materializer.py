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
"""Implementation of the PyTorch Module materializer."""

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

import cloudpickle
import torch
from torch.nn import Module

from zenml.enums import ArtifactType
from zenml.integrations.pytorch.materializers.base_pytorch_materializer import (
    BasePyTorchMaterializer,
)
from zenml.integrations.pytorch.utils import count_module_params
from zenml.io import fileio

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "entire_model.pt"
CHECKPOINT_FILENAME = "checkpoint.pt"


class PyTorchModuleMaterializer(BasePyTorchMaterializer):
    """Materializer to read/write Pytorch models.

    Inspired by the guide:
    https://pytorch.org/tutorials/beginner/saving_loading_models.html
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Module,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    FILENAME: ClassVar[str] = DEFAULT_FILENAME

    def save(self, model: Module) -> None:
        """Writes a PyTorch model, as a model and a checkpoint.

        Args:
            model: A torch.nn.Module or a dict to pass into model.save
        """
        # Save entire model to artifact directory, This is the default behavior
        # for loading model in development phase (training, evaluation)
        super().save(model)

        # Also save model checkpoint to artifact directory,
        # This is the default behavior for loading model in production phase (inference)
        if isinstance(model, Module):
            with fileio.open(
                os.path.join(self.uri, CHECKPOINT_FILENAME), "wb"
            ) as f:
                torch.save(model.state_dict(), f, pickle_module=cloudpickle)

    def extract_metadata(self, model: Module) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Model` object.

        Args:
            model: The `Model` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {**count_module_params(model)}
