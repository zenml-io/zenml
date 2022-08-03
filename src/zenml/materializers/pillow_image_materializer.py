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
"""Materializer for Pillow Image files."""

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
DEFAULT_IMAGE_FILENAME = "image.png"


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for PIL.Image objects.

    This materializer takes a dictionary of files and returns a dictionary of
    PIL image objects.
    """

    ASSOCIATED_TYPES = (PIL.Image.Image,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[PIL.Image.Image]) -> PIL.Image.Image:
        """Read from artifact store.

        Args:
            data_type: A PIL.Image.Image type.

        Returns:
            A PIL.Image.Image object.
        """
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_IMAGE_FILENAME)

        # create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_IMAGE_FILENAME)

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
        temp_image_path = os.path.join(temp_dir.name, DEFAULT_IMAGE_FILENAME)
        # save the image in a temporary directory
        image.save(temp_image_path)

        # copy the saved image to the artifact store
        io_utils.copy(temp_image_path, self.artifact.uri)
        fileio.remove(temp_image_path)
