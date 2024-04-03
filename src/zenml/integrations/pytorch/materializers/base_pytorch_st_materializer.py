#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

import torch

try:
    from safetensors.torch import load_file, save_file
except ImportError:
    raise ImportError(
        "You are using `PytorchMaterializer` with safetensors.",
        "You can install `safetensors` by running `pip install safetensors`.",
    )

from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "obj.safetensors"
DEFAULT_MODEL_FILENAME = "model_architecture.json"


class BasePyTorchSTMaterializer(BaseMaterializer):
    """Base class for PyTorch materializers."""

    FILENAME: ClassVar[str] = DEFAULT_FILENAME
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Optional[Type[Any]]) -> Any:
        """Uses `safetensors` to load a PyTorch object.

        Args:
            data_type: The type of the object to load.

        Raises:
            ValueError: If the data_type is not a nn.Module or Dict[str, torch.Tensor]

        Returns:
            The loaded PyTorch object.
        """
        obj_filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(data_type, dict):
                return load_file(obj_filename)

            # Load model architecture
            model_filename = os.path.join(self.uri, DEFAULT_MODEL_FILENAME)
            model_arch = torch.load(model_filename)
            _model = model_arch["model"]

            # Load model weights
            weights = load_file(obj_filename)
            _model.load_state_dict(weights)

            return _model
        except Exception as e:
            raise ValueError(f"Invalid data_type received: {e}")

    def save(self, obj: Any) -> None:
        """Uses `safetensors` to save a PyTorch object.

        Args:
            obj: The PyTorch object to save.

        Raises:
            ValueError: If the data_type is not a nn.Module or Dict[str, torch.Tensor]

        """
        obj_filename = os.path.join(self.uri, self.FILENAME)
        try:
            if isinstance(obj, dict):
                save_file(obj, obj_filename)
            else:
                # Save model weights
                save_file(obj.state_dict(), obj_filename)

                # Save model architecture
                model_arch = {"model": obj}
                model_filename = os.path.join(self.uri, DEFAULT_MODEL_FILENAME)
                torch.save(model_arch, model_filename)
        except Exception as e:
            raise ValueError(f"Invalid data_type received: {e}")
