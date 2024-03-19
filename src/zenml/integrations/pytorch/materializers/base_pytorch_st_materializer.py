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
"""Implementation of the PyTorch DataLoader materializer using Safetensors."""

import os
from typing import Any, ClassVar, Optional, Type

from safetensors.torch import load_file, load_model, save_file, save_model
from torch.nn import Module

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "obj.safetensors"


class BasePyTorchSTMaterializer(BaseMaterializer):
    """Base class for PyTorch materializers."""

    FILENAME: ClassVar[str] = DEFAULT_FILENAME
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, obj: Any, data_type: Optional[Type[Any]] = None) -> Any:
        """Uses `safetensors` to load a PyTorch object.

        Args:
            obj: The model to load onto.
            data_type: The type of the object to load.

        Returns:
            The loaded PyTorch object.
        """
        filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(obj, Module):
                return load_model(obj, filename)

            return load_file(obj, filename)
        except:
            raise ValueError(
                "data_type should be of type: nn.Module or Dict[str, torch.Tensor]"
            )

    def save(self, obj: Any) -> None:
        """Uses `safetensors` to save a PyTorch object.

        Args:
            obj: The PyTorch object to save.
        """
        filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(obj, Module):
                save_model(obj, filename)
            else:
                save_file(obj, filename)
        except:
            raise ValueError(
                "data_type should be of type: nn.Module or Dict[str, torch.Tensor]"
            )


# Alias for the BasePyTorchMaterializer class, allowing users that have already used
# the old name to continue using it without breaking their code.
# 'BasePyTorchMaterializer' or 'BasePyTorchMaterliazer' to refer to the same class.
BasePyTorchSTMaterliazer = BasePyTorchSTMaterializer
