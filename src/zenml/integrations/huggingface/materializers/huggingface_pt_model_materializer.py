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
"""Implementation of the Huggingface PyTorch model materializer."""

import importlib
import os
from tempfile import TemporaryDirectory
from typing import Any, ClassVar, Dict, Tuple, Type

from transformers import (
    AutoConfig,
    PreTrainedModel,
)

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import DType, MetadataType
from zenml.utils import io_utils

DEFAULT_PT_MODEL_DIR = "hf_pt_model"


class HFPTModelMaterializer(BaseMaterializer):
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
        io_utils.copy_dir(
            os.path.join(self.uri, DEFAULT_PT_MODEL_DIR), temp_dir.name
        )

        config = AutoConfig.from_pretrained(temp_dir.name)
        architecture = config.architectures[0]
        model_cls = getattr(
            importlib.import_module("transformers"), architecture
        )
        return model_cls.from_pretrained(temp_dir.name)

    def save(self, model: PreTrainedModel) -> None:
        """Writes a Model to the specified dir.

        Args:
            model: The Torch Model to write.
        """
        temp_dir = TemporaryDirectory()
        model.save_pretrained(temp_dir.name)
        io_utils.copy_dir(
            temp_dir.name,
            os.path.join(self.uri, DEFAULT_PT_MODEL_DIR),
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
