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


import tempfile
from pathlib import Path
from typing import Dict, List

from fastai.data.transforms import get_image_files
from fastai.learner import Learner
from fastai.metrics import error_rate
from fastai.vision.all import *  # noqa
from fastai.vision.augment import Resize
from fastai.vision.data import ImageDataLoaders
from fastai.vision.learner import vision_learner
from fastai.vision.models import squeezenet1_1

from zenml.integrations.label_studio.label_studio_utils import (
    download_azure_image,
)
from zenml.logger import get_logger
from zenml.steps import step
from zenml.steps.step_context import StepContext

IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

logger = get_logger(__name__)

initial_training_path = str(
    Path(__file__).parent.absolute().parent.absolute()
    / "assets"
    / "images"
    / "initial_training"
)
new_data_for_batch_inference = str(
    Path(__file__).parent.absolute().parent.absolute()
    / "assets"
    / "images"
    / "finetuning"
)


def is_aria(x: str) -> bool:
    return x.startswith("ARIA_")


@step(enable_cache=False)
def model_trainer(
    image_urls: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> Learner:
    if labels:
        with tempfile.TemporaryDirectory() as temp_dir:
            for url in image_urls:
                download_azure_image(url, temp_dir.name)

            dls = ImageDataLoaders.from_lists(
                temp_dir,
                image_urls,
                labels=labels,
                valid_pct=0.2,
                seed=42,
                item_tfms=Resize(224),
                bs=1,
            )
            learner = vision_learner(dls, squeezenet1_1, metrics=error_rate)
            learner.fine_tune(1)
            return learner
    else:
        dls = ImageDataLoaders.from_name_func(
            "/Users/strickvl/coding/zenml/repos/zenml/examples/annotation_label_studio/assets/images/initial_training",
            get_image_files(
                "/Users/strickvl/coding/zenml/repos/zenml/examples/annotation_label_studio/assets/images/initial_training"
            ),
            valid_pct=0.2,
            seed=42,
            label_func=is_aria,
            item_tfms=Resize(224),
            bs=1,
        )
        learner = vision_learner(dls, squeezenet1_1, metrics=error_rate)
        learner.fine_tune(1)
        return learner
