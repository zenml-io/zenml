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
from contextlib import ExitStack as does_not_raise

from PIL import Image

from zenml.integrations.pillow.materializers.pillow_image_materializer import (
    PillowImageMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step


def test_materializer_works_for_pillow_image_objects(clean_repo):
    """Check the materializer is able to handle PIL image objects."""

    @step
    def read_image() -> Image.Image:
        """Reads and materializes an image file."""
        return Image.new("RGB", (10, 10), color="red")

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

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    image = last_run.steps[-1].output.read()
    assert isinstance(image, Image.Image)
