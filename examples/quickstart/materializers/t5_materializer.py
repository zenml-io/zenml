# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import shutil
import tempfile
import zipfile
from typing import Any, ClassVar, Type, Union

from transformers import T5ForConditionalGeneration, T5Tokenizer

from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "t5_model_dir.zip"


class T5Materializer(BaseMaterializer):
    """Base class for ultralytics YOLO models."""

    FILENAME: ClassVar[str] = DEFAULT_FILENAME
    SKIP_REGISTRATION: ClassVar[bool] = True
    ASSOCIATED_TYPES = (T5ForConditionalGeneration,T5Tokenizer,)

    def load(self, data_type: Type[Any]) -> Union[T5ForConditionalGeneration, T5Tokenizer]:
        """Reads a T5ForConditionalGeneration model or T5Tokenizer from a serialized zip file.

        Args:
            data_type: A T5ForConditionalGeneration or T5Tokenizer type.

        Returns:
            A T5ForConditionalGeneration or T5Tokenizer object.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        with tempfile.TemporaryDirectory(prefix="zenml-temp-") as temp_dir:
            temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

            # Copy from artifact store to temporary file
            fileio.copy(filepath, temp_file)

            # Extract the zip file
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Load the model or tokenizer from the extracted directory
            if data_type == T5ForConditionalGeneration:
                return T5ForConditionalGeneration.from_pretrained(temp_dir)
            elif data_type == T5Tokenizer:
                return T5Tokenizer.from_pretrained(temp_dir)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")

    def save(self, obj: Union[T5ForConditionalGeneration, T5Tokenizer]) -> None:
        """Creates a serialization for a T5ForConditionalGeneration model or T5Tokenizer.

        Args:
            obj: A T5ForConditionalGeneration model or T5Tokenizer.
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory(prefix="zenml-temp-") as temp_dir:
            # Save the model or tokenizer
            obj.save_pretrained(temp_dir)

            # Compress the directory into a zip file
            zip_path = os.path.join(temp_dir, "t5_object.zip")
            shutil.make_archive(os.path.join(temp_dir, "t5_object"), 'zip', temp_dir)

            # Copy the zip file to the artifact store
            filepath = os.path.join(self.uri, DEFAULT_FILENAME)
            fileio.copy(zip_path, filepath)
