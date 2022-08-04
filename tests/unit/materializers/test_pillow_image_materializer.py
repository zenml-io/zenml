#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import os
from contextlib import ExitStack as does_not_raise

import PIL

from zenml.materializers.pillow_image_materializer import (
    PillowImageMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step

JPEG_FILE_PATH = os.path.join(
    "/".join(os.path.dirname(__file__).split("/")[:-3]),
    "examples/label_studio_annotation/data/batch_1/2dc5fe08-152d-47d0-bdd4-f70ddbfb6486.jpeg",
)


def test_materializer_works_for_image_files(clean_repo):
    """..."""

    @step
    def read_image() -> PIL.Image.Image:
        """Reads and materializes an image file."""
        return PIL.Image.open(JPEG_FILE_PATH)

    @pipeline
    def test_pipeline(image_reader) -> None:
        """Tests the PillowImageMaterializer."""
        image_reader()

    with does_not_raise():
        test_pipeline(
            image_reader=read_image().with_return_materializers(
                PillowImageMaterializer
            )
        ).run()

    image = (
        clean_repo.get_pipeline("test_pipeline")
        .runs[-1]
        .steps[-1]
        .output.read()
    )
    assert isinstance(image, PIL.Image.Image)
