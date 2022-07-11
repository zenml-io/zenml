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
import tempfile
from typing import Dict, List

from fastai.learner import Learner
from fastai.vision.all import *

from zenml.integrations.label_studio.label_studio_utils import download_image
from zenml.logger import get_logger
from zenml.steps import step
from zenml.steps.step_context import StepContext

LOCAL_IMAGE_FILES = "./assets/images/"
IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

logger = get_logger(__name__)


@step
def fine_tuning_step(
    old_model: Learner,
    training_images: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> Learner:
    with tempfile.TemporaryDirectory() as temp_dir:
        for url in training_images:
            download_image(url, temp_dir.name)

        training_images = glob.glob(f"{temp_dir.name}/*{IMAGE_REGEX_FILTER}")

        dls = ImageDataLoaders.from_name_func(
            temp_dir,
            get_image_files(temp_dir),
            valid_pct=0.2,
            seed=42,
            label_func=is_cat,
            item_tfms=Resize(224),
        )

        learn = vision_learner(dls, old_model, metrics=error_rate)
        learn.fine_tune(1)
