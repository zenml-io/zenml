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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

from PIL import Image

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)

DEFAULT_IMAGE_FILENAME = "image_file"
DEFAULT_IMAGE_EXTENSION = "PNG"


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for Image.Image objects.

    This materializer takes a PIL image object and returns a PIL image object.
    It handles all the source image formats supported by PIL as listed here:
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Image.Image,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Image.Image]) -> Image.Image:
        """Read from artifact store.

        Args:
            data_type: An Image.Image type.

        Returns:
            An Image.Image object.
        """
        files = io_utils.find_files(self.uri, f"{DEFAULT_IMAGE_FILENAME}.*")
        filepath = [file for file in files if not fileio.isdir(file)][0]

        # create a temporary folder
        temp_dir = tempfile.TemporaryDirectory(prefix="zenml-temp-")
        temp_file = os.path.join(
            temp_dir.name,
            f"{DEFAULT_IMAGE_FILENAME}{os.path.splitext(filepath)[1]}",
        )

        # copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        return Image.open(temp_file)

    def save(self, image: Image.Image) -> None:
        """Write to artifact store.

        Args:
            image: An Image.Image object.
        """
        temp_dir = tempfile.TemporaryDirectory(prefix="zenml-temp-")
        file_extension = image.format or DEFAULT_IMAGE_EXTENSION
        full_filename = f"{DEFAULT_IMAGE_FILENAME}.{file_extension}"
        temp_image_path = os.path.join(temp_dir.name, full_filename)

        # save the image in a temporary directory
        image.save(temp_image_path)

        # copy the saved image to the artifact store
        artifact_store_path = os.path.join(self.uri, full_filename)
        io_utils.copy(temp_image_path, artifact_store_path, overwrite=True)  # type: ignore[attr-defined]
        temp_dir.cleanup()

    def save_visualizations(
        self, image: Image.Image
    ) -> Dict[str, VisualizationType]:
        """Finds and saves the given image as a visualization.

        Args:
            image: The image to save as a visualization.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        file_extension = image.format or DEFAULT_IMAGE_EXTENSION
        full_filename = f"{DEFAULT_IMAGE_FILENAME}.{file_extension}"
        artifact_store_path = os.path.join(self.uri, full_filename)
        artifact_store_path = artifact_store_path.replace("\\", "/")
        return {artifact_store_path: VisualizationType.IMAGE}

    def extract_metadata(
        self, image: Image.Image
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Image` object.

        Args:
            image: The `Image` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        metadata = {
            "width": image.width,
            "height": image.height,
            "mode": str(image.mode),
        }
        if hasattr(image, "filename"):
            metadata["original_filename"] = str(image.filename)
        return metadata  # type: ignore[return-value]
