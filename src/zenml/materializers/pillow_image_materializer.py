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

import PIL

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

logger = get_logger(__name__)

DEFAULT_IMAGE_FILENAME = "image_file"


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for PIL.Image.Image objects.

    This materializer takes a PIL image object and returns a PIL image object.
    It handles all the source image formats supported by PIL as listed here:
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html.
    """

    ASSOCIATED_TYPES = (PIL.Image.Image,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(
        self, data_type: Type[PIL.Image.Image]
    ) -> PIL.Image.Image:
        """Read from artifact store.

        Args:
            data_type: A PIL.Image.Image type.

        Returns:
            A PIL.Image.Image object.
        """
        super().handle_input(data_type)
        files = io_utils.find_files(
            self.artifact.uri, f"{DEFAULT_IMAGE_FILENAME}.*"
        )
        filepath = [file for file in files if not fileio.isdir(file)][0]

        # create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(
            str(temp_dir),
            f"{DEFAULT_IMAGE_FILENAME}{os.path.splitext(filepath)[1]}",
        )

        # copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        image = PIL.Image.open(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)
        return image

    def handle_return(self, image: PIL.Image.Image) -> None:
        """Write to artifact store.

        Args:
            image: A PIL.Image.Image object.
        """
        super().handle_return(image)
        temp_dir = tempfile.TemporaryDirectory()
        file_extension = image.format.lower()
        full_filename = f"{DEFAULT_IMAGE_FILENAME}.{file_extension}"
        temp_image_path = os.path.join(temp_dir.name, full_filename)
        artifact_store_path = os.path.join(self.artifact.uri, full_filename)

        # save the image in a temporary directory
        image.save(temp_image_path)

        # copy the saved image to the artifact store
        io_utils.copy(temp_image_path, artifact_store_path, overwrite=True)
        fileio.remove(temp_image_path)
