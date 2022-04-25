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

import os
from tempfile import TemporaryDirectory
from typing import Any, Type

from transformers import AutoTokenizer
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from zenml.artifacts import ModelArtifact
from zenml.io import utils as fileio_utils
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_TOKENIZER_DIR = "hf_tokenizer"


class HFTokenizerMaterializer(BaseMaterializer):
    """Materializer to read tokenizer to and from huggingface tokenizer."""

    ASSOCIATED_TYPES = (PreTrainedTokenizerBase,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> PreTrainedTokenizerBase:
        """Reads Tokenizer"""
        super().handle_input(data_type)

        return AutoTokenizer.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR)
        )

    def handle_return(self, tokenizer: Type[Any]) -> None:
        """Writes a Tokenizer to the specified dir.
        Args:
            PreTrainedTokenizerBase: The HFTokenizer to write.
        """
        super().handle_return(tokenizer)
        temp_dir = TemporaryDirectory()
        tokenizer.save_pretrained(temp_dir.name)
        fileio_utils.copy_dir(
            temp_dir.name,
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR),
        )
