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
"""Implementation of the Huggingface t5 materializer."""

import os
import tempfile
from typing import Any, ClassVar, Type, Union

from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    T5TokenizerFast,
)

from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class HFT5Materializer(BaseMaterializer):
    """Base class for huggingface t5 models."""

    SKIP_REGISTRATION: ClassVar[bool] = False
    ASSOCIATED_TYPES = (
        T5ForConditionalGeneration,
        T5Tokenizer,
        T5TokenizerFast,
    )

    def load(
        self, data_type: Type[Any]
    ) -> Union[T5ForConditionalGeneration, T5Tokenizer, T5TokenizerFast]:
        """Reads a T5ForConditionalGeneration model or T5Tokenizer from a serialized zip file.

        Args:
            data_type: A T5ForConditionalGeneration or T5Tokenizer type.

        Returns:
            A T5ForConditionalGeneration or T5Tokenizer object.

        Raises:
            ValueError: Unsupported data type used
        """
        filepath = self.uri

        with tempfile.TemporaryDirectory(prefix="zenml-temp-") as temp_dir:
            # Copy files from artifact store to temporary directory
            for file in fileio.listdir(filepath):
                src = os.path.join(filepath, file)
                dst = os.path.join(temp_dir, file)
                if fileio.isdir(src):
                    fileio.makedirs(dst)
                    for subfile in fileio.listdir(src):
                        subsrc = os.path.join(src, subfile)
                        subdst = os.path.join(dst, subfile)
                        fileio.copy(subsrc, subdst)
                else:
                    fileio.copy(src, dst)

            # Load the model or tokenizer from the temporary directory
            if data_type in [T5ForConditionalGeneration, T5Tokenizer, T5TokenizerFast]:
                return data_type.from_pretrained(temp_dir)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")

    def save(
        self,
        obj: Union[T5ForConditionalGeneration, T5Tokenizer, T5TokenizerFast],
    ) -> None:
        """Creates a serialization for a T5ForConditionalGeneration model or T5Tokenizer.

        Args:
            obj: A T5ForConditionalGeneration model or T5Tokenizer.
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory(prefix="zenml-temp-") as temp_dir:
            # Save the model or tokenizer
            obj.save_pretrained(temp_dir)

            # Copy the directory to the artifact store
            filepath = self.uri
            fileio.makedirs(filepath)
            for file in os.listdir(temp_dir):
                src = os.path.join(temp_dir, file)
                dst = os.path.join(filepath, file)
                if os.path.isdir(src):
                    fileio.makedirs(dst)
                    for subfile in os.listdir(src):
                        subsrc = os.path.join(src, subfile)
                        subdst = os.path.join(dst, subfile)
                        fileio.copy(subsrc, subdst)
                else:
                    fileio.copy(src, dst)
