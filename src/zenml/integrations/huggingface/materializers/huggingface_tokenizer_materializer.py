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
"""Implementation of the Huggingface tokenizer materializer."""

import os
from tempfile import TemporaryDirectory
from typing import Any, Type

from transformers import AutoTokenizer  # type: ignore [import]
from transformers.tokenization_utils_base import (  # type: ignore [import]
    PreTrainedTokenizerBase,
)

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

DEFAULT_TOKENIZER_DIR = "hf_tokenizer"


class HFTokenizerMaterializer(BaseMaterializer):
    """Materializer to read tokenizer to and from huggingface tokenizer."""

    ASSOCIATED_TYPES = (PreTrainedTokenizerBase,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> PreTrainedTokenizerBase:
        """Reads Tokenizer.

        Args:
            data_type: The type of the tokenizer to read.

        Returns:
            The tokenizer read from the specified dir.
        """
        super().load(data_type)

        return AutoTokenizer.from_pretrained(
            os.path.join(self.uri, DEFAULT_TOKENIZER_DIR)
        )

    def save(self, tokenizer: Type[Any]) -> None:
        """Writes a Tokenizer to the specified dir.

        Args:
            tokenizer: The HFTokenizer to write.
        """
        super().save(tokenizer)
        temp_dir = TemporaryDirectory()
        tokenizer.save_pretrained(temp_dir.name)
        io_utils.copy_dir(
            temp_dir.name,
            os.path.join(self.uri, DEFAULT_TOKENIZER_DIR),
        )
