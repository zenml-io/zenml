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
"""Implementation of the Huggingface PyTorch model materializer using Safetensors."""

import os
from typing import Any, ClassVar, Dict, Tuple, Type

import torch
from transformers import (  # type: ignore [import-untyped]
    PreTrainedModel,
)

try:
    from safetensors.torch import load_file, save_file
except ImportError:
    raise ImportError(
        "You are using `HFMaterializer` with safetensors.",
        "You can install `safetensors` by running `pip install safetensors`.",
    )

from tempfile import TemporaryDirectory

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import DType, MetadataType
from zenml.utils import io_utils

DEFAULT_FILENAME = "model.safetensors"
DEFAULT_MODEL_FILENAME = "model_architecture.json"


class HFPTModelSTMaterializer(BaseMaterializer):
    """Materializer to read torch model to and from huggingface pretrained model."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (PreTrainedModel,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL

    def load(self, data_type: Type[PreTrainedModel]) -> PreTrainedModel:
        """Reads HFModel.

        Args:
            data_type: The type of the model to read.

        Returns:
            The model read from the specified dir.
        """
        temp_dir = TemporaryDirectory()
        io_utils.copy_dir(self.uri, temp_dir.name)
        # Load model architecture
        model_filename = os.path.join(temp_dir.name, DEFAULT_MODEL_FILENAME)
        model_arch = torch.load(model_filename)
        _model = model_arch["model"]

        # Load model weight
        obj_filename = os.path.join(temp_dir.name, DEFAULT_FILENAME)
        weights = load_file(obj_filename)
        _model.load_state_dict(weights)

        return _model

    def save(self, model: PreTrainedModel) -> None:
        """Writes a Model to the specified dir.

        Args:
            model: The Torch Model to write.
        """
        temp_dir = TemporaryDirectory()

        # Save model weights
        obj_filename = os.path.join(temp_dir.name, DEFAULT_FILENAME)
        save_file(model.state_dict(), obj_filename)

        # Save model architecture
        model_arch = {"model": model}
        model_filename = os.path.join(temp_dir.name, DEFAULT_MODEL_FILENAME)
        torch.save(model_arch, model_filename)

        io_utils.copy_dir(
            temp_dir.name,
            self.uri,
        )

    def extract_metadata(
        self, model: PreTrainedModel
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `PreTrainedModel` object.

        Args:
            model: The `PreTrainedModel` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        from zenml.integrations.pytorch.utils import count_module_params

        module_param_metadata = count_module_params(model)
        return {
            **module_param_metadata,
            "dtype": DType(str(model.dtype)),
            "device": str(model.device),
        }
