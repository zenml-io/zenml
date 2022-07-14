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

from fastai.data.transforms import get_image_files
from fastai.learner import Learner
from fastai.metrics import error_rate
from fastai.vision.augment import Resize
from fastai.vision.data import ImageDataLoaders
from fastai.vision.learner import vision_learner

from zenml.integrations.label_studio.label_studio_utils import (
    download_azure_image,
)
from zenml.logger import get_logger
from zenml.steps import step
from zenml.steps.step_context import StepContext


from __future__ import print_function
from __future__ import division
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import time
import os
import copy
from pathlib import Path

IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

logger = get_logger(__name__)

initial_training_path = str(
    Path(__file__).parent.absolute().parent.absolute()
    / "assets" / "images" / "initial_training"
)
finetuning_path = str(
    Path(__file__).parent.absolute().parent.absolute()
    / "assets" / "images" / "finetuning"
)

# Top level data directory. Here we assume the format of the directory conforms
#   to the ImageFolder structure
data_dir = initial_training_path
model_name = "squeezenet"
num_classes = 2
batch_size = 2
num_epochs = 5

# Flag for feature extracting. When False, we finetune the whole model,
#   when True we only update the reshaped layer params
feature_extract = True


@step
def fine_tuning_step(
    training_images: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> PyTorchModel:
    with tempfile.TemporaryDirectory() as temp_dir:
        for url in training_images:
            download_azure_image(url, temp_dir.name)

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
