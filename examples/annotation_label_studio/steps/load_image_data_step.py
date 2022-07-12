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
from typing import Dict

from PIL import Image

from zenml.steps import Output, step
from zenml.steps.step_context import StepContext

LOCAL_IMAGE_FILES = str(Path(__file__).parent.absolute() / "assets/images")


@step(enable_cache=False)
def load_image_data(context: StepContext) -> Output(images=Dict, uri=str):
    """Gets images from a cloud artifact store directory."""
    image_files = glob.glob(f"{LOCAL_IMAGE_FILES}/*.jpeg")
    return {
        os.path.basename(image_file): Image.open(image_file)
        for image_file in image_files
    }, context.get_output_artifact_uri("images")
