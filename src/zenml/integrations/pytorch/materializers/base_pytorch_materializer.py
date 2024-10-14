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
from typing import Any, ClassVar, Type

import cloudpickle
import torch

from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "obj.pt"


class BasePyTorchMaterializer(BaseMaterializer):
    """Base class for PyTorch materializers."""

    FILENAME: ClassVar[str] = DEFAULT_FILENAME
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Type[Any]) -> Any:
        """Uses `torch.load` to load a PyTorch object.

        Args:
            data_type: The type of the object to load.

        Returns:
            The loaded PyTorch object.
        """
        with fileio.open(os.path.join(self.uri, self.FILENAME), "rb") as f:
            # NOTE (security): The `torch.load` function uses `pickle` as
            # the default unpickler, which is NOT secure. This materializer
            # is intended for use with trusted data sources.
            return torch.load(f)  # nosec

    def save(self, obj: Any) -> None:
        """Uses `torch.save` to save a PyTorch object.

        Args:
            obj: The PyTorch object to save.
        """
        with fileio.open(os.path.join(self.uri, self.FILENAME), "wb") as f:
            # NOTE (security): The `torch.save` function uses `cloudpickle` as
            # the default unpickler, which is NOT secure. This materializer
            # is intended for use with trusted data sources.
            torch.save(obj, f, pickle_module=cloudpickle)  # nosec


# Alias for the BasePyTorchMaterializer class, allowing users that have already used
# the old name to continue using it without breaking their code.
# 'BasePyTorchMaterializer' or 'BasePyTorchMaterliazer' to refer to the same class.
BasePyTorchMaterliazer = BasePyTorchMaterializer
