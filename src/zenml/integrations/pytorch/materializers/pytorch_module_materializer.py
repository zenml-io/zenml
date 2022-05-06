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

import os
from typing import Any, Type

import torch
from torch.nn import Module  # type: ignore[attr-defined]

from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "entire_model.pt"
CHECKPOINT_FILENAME = "checkpoint.pt"


class PyTorchModuleMaterializer(BaseMaterializer):
    """Materializer to read/write Pytorch models. Inspired by the guide:
    https://pytorch.org/tutorials/beginner/saving_loading_models.html"""

    ASSOCIATED_TYPES = (Module,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Module:
        """Reads and returns a PyTorch model. Only loads the model, not
        the checkpoint.

        Returns:
            A loaded pytorch model.
        """
        super().handle_input(data_type)
        with fileio.open(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME), "rb"
        ) as f:
            return torch.load(f)  # type: ignore[no-untyped-call]  # noqa

    def handle_return(self, model: Module) -> None:
        """Writes a PyTorch model, as a model and a checkpoint.

        Args:
            model: A torch.nn.Module or a dict to pass into model.save
        """
        super().handle_return(model)

        # Save entire model to artifact directory, This is the default behavior
        # for loading model in development phase (training, evaluation)
        with fileio.open(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME), "wb"
        ) as f:
            torch.save(model, f)

        # Also save model checkpoint to artifact directory,
        # This is the default behavior for loading model in production phase (inference)
        if isinstance(model, Module):
            with fileio.open(
                os.path.join(self.artifact.uri, CHECKPOINT_FILENAME), "wb"
            ) as f:
                torch.save(model.state_dict(), f)
