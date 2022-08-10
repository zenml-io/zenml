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
"""Materializer for Pillow Image objects."""

import os
import tempfile
from typing import Type

from PIL import Image

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

logger = get_logger(__name__)

DEFAULT_IMAGE_FILENAME = "image_file"


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for Image.Image objects.

    This materializer takes a PIL image object and returns a PIL image object.
    It handles all the source image formats supported by PIL as listed here:
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html.
    """

    ASSOCIATED_TYPES = (Image.Image,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Image.Image]) -> Image.Image:
        """Read from artifact store.

        Args:
            data_type: An Image.Image type.

        Returns:
            An Image.Image object.
        """
        super().handle_input(data_type)
        files = io_utils.find_files(
            self.artifact.uri, f"{DEFAULT_IMAGE_FILENAME}*"
        )
        filepath = [file for file in files if not fileio.isdir(file)][0]

        # create a temporary folder
        file_extension = os.path.splitext(filepath)[-1]
        with tempfile.NamedTemporaryFile(suffix=file_extension) as f:
            # copy from artifact store to temporary file
            io_utils.copy(filepath, f.name, overwrite=True)  # type: ignore[attr-defined]
            image = Image.open(f.name)
        return image

    def handle_return(self, image: Image.Image) -> None:
        """Write to artifact store.

        Args:
            image: An Image.Image object.
        """
        super().handle_return(image)

        file_extension = image.format or "PNG"
        full_filename = f"{DEFAULT_IMAGE_FILENAME}.{file_extension}"
        artifact_store_path = os.path.join(self.artifact.uri, full_filename)

        # save the image in a temporary file
        with tempfile.NamedTemporaryFile(
            prefix=DEFAULT_IMAGE_FILENAME, suffix=f".{file_extension.lower()}"
        ) as f:
            image.save(f.name)
            # copy the saved image to the artifact store
            io_utils.copy(f.name, artifact_store_path, overwrite=True)  # type: ignore[attr-defined]
