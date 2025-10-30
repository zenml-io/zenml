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
from typing import Any, ClassVar

from transformers import AutoTokenizer
from transformers.tokenization_utils_base import (
    PreTrainedTokenizerBase,
)

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

DEFAULT_TOKENIZER_DIR = "hf_tokenizer"


class HFTokenizerMaterializer(BaseMaterializer):
    """Materializer to read tokenizer to and from huggingface tokenizer."""

    ASSOCIATED_TYPES: ClassVar[tuple[type[Any], ...]] = (
        PreTrainedTokenizerBase,
    )
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL

    def load(self, data_type: type[Any]) -> PreTrainedTokenizerBase:
        """Reads Tokenizer.

        Args:
            data_type: The type of the tokenizer to read.

        Returns:
            The tokenizer read from the specified dir.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            io_utils.copy_dir(
                os.path.join(self.uri, DEFAULT_TOKENIZER_DIR), temp_dir
            )
            return AutoTokenizer.from_pretrained(temp_dir)

    def save(self, tokenizer: type[Any]) -> None:
        """Writes a Tokenizer to the specified dir.

        Args:
            tokenizer: The HFTokenizer to write.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            tokenizer.save_pretrained(temp_dir)
            io_utils.copy_dir(
                temp_dir,
                os.path.join(self.uri, DEFAULT_TOKENIZER_DIR),
            )
