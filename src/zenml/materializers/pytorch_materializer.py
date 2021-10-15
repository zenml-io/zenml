#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Type, Union

import torch

from zenml.materializers.base_materializer import BaseMaterializer
from zenml.types.pytorch_types import TorchDict

DEFAULT_FILENAME = "entire_model.pt"


class PyTorchMaterializer(BaseMaterializer):
    """Materializer to read/write Pytorch models."""

    ASSOCIATED_TYPES = [torch.nn.Module, TorchDict]

    def handle_input(
        self, data_type: Type
    ) -> Union[torch.nn.Module, TorchDict]:
        """Reads and returns a PyTorch model.

        Returns:
            A loaded pytorch model.
        """
        super().handle_input(data_type)
        return torch.load(os.path.join(self.artifact.uri, DEFAULT_FILENAME))

    def handle_return(self, model: Union[torch.nn.Module, TorchDict]):
        """Writes a PyTorch model.

        Args:
            model: A torch.nn.Module or a dict to pass into model.save
        """
        super().handle_return(model)
        model.save(os.path.join(self.artifact.uri, DEFAULT_FILENAME))
