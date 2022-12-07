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
from typing import Any, Type

from transformers import AutoConfig, PreTrainedModel  # type: ignore [import]

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

DEFAULT_PT_MODEL_DIR = "hf_pt_model"


class HFPTModelMaterializer(BaseMaterializer):
    """Materializer to read torch model to and from huggingface pretrained model."""

    ASSOCIATED_TYPES = (PreTrainedModel,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> PreTrainedModel:
        """Reads HFModel.

        Args:
            data_type: The type of the model to read.

        Returns:
            The model read from the specified dir.
        """
        super().load(data_type)

        config = AutoConfig.from_pretrained(
            os.path.join(self.uri, DEFAULT_PT_MODEL_DIR)
        )
        architecture = config.architectures[0]
        model_cls = getattr(
            importlib.import_module("transformers"), architecture
        )
        return model_cls.from_pretrained(
            os.path.join(self.uri, DEFAULT_PT_MODEL_DIR)
        )

    def save(self, model: Type[Any]) -> None:
        """Writes a Model to the specified dir.

        Args:
            model: The Torch Model to write.
        """
        super().save(model)
        temp_dir = TemporaryDirectory()
        model.save_pretrained(temp_dir.name)
        io_utils.copy_dir(
            temp_dir.name,
            os.path.join(self.uri, DEFAULT_PT_MODEL_DIR),
        )
