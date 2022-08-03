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
from typing import Dict, Type, Any

import PIL

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

logger = get_logger(__name__)
IMAGE_FILENAME = "image.png"


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for PIL.Image objects.

    This materializer takes a dictionary of files and returns a dictionary of
    PIL image objects.
    """

    ASSOCIATED_TYPES = (PIL.Image.Image,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(
        self, data_type: Type[PIL.Image.Image]
    ) -> PIL.Image.Image:
        """Read from artifact store"""
        super().handle_input(data_type)
        temp_dir = tempfile.TemporaryDirectory()
        io_utils.copy_dir(self.artifact.uri, temp_dir.name)

        files = [
            f"{temp_dir.name}/{filename}"
            for filename in fileio.listdir(temp_dir.name)
        ]
        images_dict = {}
        for filename in files:
            with fileio.open(filename, "rb") as f:
                image = PIL.Image.open(f)
                image.load()
                images_dict[filename] = image

        fileio.rmtree(temp_dir.name)
        return images_dict

    def handle_return(self, image: PIL.Image.Image) -> None:
        """Write to artifact store"""
        super().handle_return(image)
        temp_dir = tempfile.TemporaryDirectory()
        temp_image_path = os.path.join(temp_dir.name, IMAGE_FILENAME)
        # save the image in a temporary directory
        image.save(temp_image_path)

        # copy the saved image to the artifact store
        io_utils.copy(temp_image_path, self.artifact.uri)
        fileio.remove(temp_image_path)
