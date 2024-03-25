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

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "obj.safetensors"


class BasePyTorchSTMaterializer(BaseMaterializer):
    """Base class for PyTorch materializers."""

    FILENAME: ClassVar[str] = DEFAULT_FILENAME
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Optional[Type[Any]], obj: Any) -> Any:
        """Uses `safetensors` to load a PyTorch object.

        Args:
            data_type: The type of the object to load.
            obj: The model to load onto.

        Raises:
            ValueError: If the data_type is not a nn.Module or Dict[str, torch.Tensor]

        Returns:
            The loaded PyTorch object.
        """
        filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(obj, dict):
                return load_file(filename)

            load_model(obj, filename)
            return obj
        except Exception as e:
            raise ValueError(f"Invalid data_type received: {e}")

    def save(self, obj: Any) -> None:
        """Uses `safetensors` to save a PyTorch object.

        Args:
            obj: The PyTorch object to save.

        Raises:
            ValueError: If the data_type is not a nn.Module or Dict[str, torch.Tensor]

        """
        filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(obj, dict):
                save_file(obj, filename)
            else:
                save_model(obj, filename)
        except Exception as e:
            raise ValueError(f"Invalid data_type received: {e}")


# Alias for the BasePyTorchMaterializer class, allowing users that have already used
# the old name to continue using it without breaking their code.
# 'BasePyTorchMaterializer' or 'BasePyTorchMaterliazer' to refer to the same class.
BasePyTorchSTMaterliazer = BasePyTorchSTMaterializer
