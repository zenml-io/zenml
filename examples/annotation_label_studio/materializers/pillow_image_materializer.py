import os
import tempfile
from typing import Dict, Type

from PIL import Image

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

logger = get_logger(__name__)


class PillowImageMaterializer(BaseMaterializer):
    """Materializer for PIL.Image objects.

    This materializer takes a dictionary of files and returns a dictionary of
    PIL image objects.
    """

    ASSOCIATED_TYPES = (dict,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Dict]) -> Dict:
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
                image = Image.open(f)
                image.load()
                images_dict[filename] = image

        fileio.rmtree(temp_dir.name)
        return images_dict

    def handle_return(self, images: Dict) -> None:
        """Write to artifact store"""
        super().handle_return(images)
        temp_dir = tempfile.TemporaryDirectory()
        for image_name, img in images.items():
            img.save(os.path.join(temp_dir.name, image_name))
        io_utils.copy_dir(temp_dir.name, self.artifact.uri)
        fileio.rmtree(temp_dir.name)
