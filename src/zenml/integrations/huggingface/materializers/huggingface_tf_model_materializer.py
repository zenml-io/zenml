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

import importlib
import os
from tempfile import TemporaryDirectory
from typing import Any, Type

from transformers import AutoConfig, TFPreTrainedModel

from zenml.artifacts import ModelArtifact
from zenml.io import utils as fileio_utils
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_TF_MODEL_DIR = "hf_tf_model"


class HFTFModelMaterializer(BaseMaterializer):
    """Materializer to read tensorflow model to and from huggingface pretrained model."""

    ASSOCIATED_TYPES = (TFPreTrainedModel,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> TFPreTrainedModel:
        """Reads HFModel"""
        super().handle_input(data_type)

        config = AutoConfig.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR)
        )
        architecture = "TF" + config.architectures[0]
        model_cls = getattr(
            importlib.import_module("transformers"), architecture
        )
        return model_cls.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR)
        )

    def handle_return(self, model: Type[Any]) -> None:
        """Writes a Model to the specified dir.
        Args:
            TFPreTrainedModel: The TF Model to write.
        """
        super().handle_return(model)
        temp_dir = TemporaryDirectory()
        model.save_pretrained(temp_dir.name)
        fileio_utils.copy_dir(
            temp_dir.name,
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR),
        )
