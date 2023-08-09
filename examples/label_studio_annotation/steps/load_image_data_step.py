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

import glob
import os
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from zenml import step
from zenml.integrations.pillow.materializers.pillow_image_materializer import (
    DEFAULT_IMAGE_FILENAME,
)
from zenml.steps import Output, StepContext


@step(enable_cache=False)
def load_image_data(
    context: StepContext,
    base_path: Optional[str] = None,
    dir_name: str = "batch_1",
) -> Output(images=Dict, uri=str):
    """Gets images from a cloud artifact store directory."""
    if base_path is None:
        base_path = str(
            Path(__file__).parent.absolute().parent.absolute() / "data"
        )
    image_dir_path = os.path.join(base_path, dir_name)
    image_files = glob.glob(f"{image_dir_path}/*.jpeg")
    uri = context.get_output_artifact_uri("images")

    images = {}
    for i, image_file in enumerate(image_files):
        image = Image.open(image_file)
        image.load()
        artifact_filepath = (
            f"{uri}/1/{i}/{DEFAULT_IMAGE_FILENAME}.{image.format}"
        )

        images[artifact_filepath] = image

    return images, uri
