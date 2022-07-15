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


from __future__ import division, print_function


import copy
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn
import torch.optim as optim
from fastai.data.transforms import get_image_files
from fastai.learner import Learner
from fastai.metrics import error_rate
from fastai.vision.augment import Resize
from fastai.vision.data import ImageDataLoaders
from fastai.vision.learner import vision_learner
from torchvision import datasets, models, transforms

from zenml.integrations.label_studio.label_studio_utils import (
    download_azure_image,
)
from zenml.logger import get_logger
from zenml.steps import step
from zenml.steps.step_context import StepContext

IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

logger = get_logger(__name__)


pytorch_initial_training_path = str(
    Path(__file__).parent.absolute().parent.absolute()
    / "assets"
    / "images"
    / "initial_pytorch_training"
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
def fastai_model_trainer(
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


def train_model(
    model,
    dataloaders,
    criterion,
    optimizer,
    num_epochs=25,
    is_inception=False,
):
    since = time.time()

    val_acc_history = []

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    for epoch in range(num_epochs):
        print("Epoch {}/{}".format(epoch, num_epochs - 1))
        print("-" * 10)

        # Each epoch has a training and validation phase
        for phase in ["train", "val"]:
            if phase == "train":
                model.train()  # Set model to training mode
            else:
                model.eval()  # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == "train"):
                    # Get model outputs and calculate loss
                    # Special case for inception because in training it has an auxiliary output. In train
                    #   mode we calculate the loss by summing the final output and the auxiliary output
                    #   but in testing we only consider the final output.
                    if is_inception and phase == "train":
                        # From https://discuss.pytorch.org/t/how-to-optimize-inception-model-with-auxiliary-classifiers/7958
                        outputs, aux_outputs = model(inputs)
                        loss1 = criterion(outputs, labels)
                        loss2 = criterion(aux_outputs, labels)
                        loss = loss1 + 0.4 * loss2
                    else:
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)

                    _, preds = torch.max(outputs, 1)

                    # backward + optimize only if in training phase
                    if phase == "train":
                        loss.backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.double() / len(
                dataloaders[phase].dataset
            )

            print(
                "{} Loss: {:.4f} Acc: {:.4f}".format(
                    phase, epoch_loss, epoch_acc
                )
            )

            # deep copy the model
            if phase == "val" and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
            if phase == "val":
                val_acc_history.append(epoch_acc)

        print()

    time_elapsed = time.time() - since
    print(
        "Training complete in {:.0f}m {:.0f}s".format(
            time_elapsed // 60, time_elapsed % 60
        )
    )
    print("Best val Acc: {:4f}".format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, val_acc_history


def set_parameter_requires_grad(model, feature_extracting):
    if feature_extracting:
        for param in model.parameters():
            param.requires_grad = False


@step(enable_cache=False)
def pytorch_model_trainer(
    image_urls: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> nn.Module:
    if labels:
        print("training with pytorch when there are labels")
    else:

        # Flag for feature extracting. When False, we finetune the whole model,
        #   when True we only update the reshaped layer params
        feature_extract = True
        data_dir = pytorch_initial_training_path
        model_name = "squeezenet"
        num_classes = 2
        batch_size = 2
        num_epochs = 5
        input_size = 224
        device = "cpu"

        data_transforms = {
            "train": transforms.Compose(
                [
                    transforms.RandomResizedCrop(input_size),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                    ),
                ]
            ),
            "val": transforms.Compose(
                [
                    transforms.Resize(input_size),
                    transforms.CenterCrop(input_size),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                    ),
                ]
            ),
        }

        # Create training and validation datasets
        image_datasets = {
            x: datasets.ImageFolder(
                os.path.join(data_dir, x), data_transforms[x]
            )
            for x in ["train", "val"]
        }
        # Create training and validation dataloaders
        dataloaders_dict = {
            x: torch.utils.data.DataLoader(
                image_datasets[x],
                batch_size=batch_size,
                shuffle=True,
                num_workers=4,
            )
            for x in ["train", "val"]
        }

        model_ft = models.squeezenet1_0(pretrained=True)
        set_parameter_requires_grad(model_ft, feature_extract)
        model_ft.classifier[1] = nn.Conv2d(
            512, num_classes, kernel_size=(1, 1), stride=(1, 1)
        )
        model_ft.num_classes = num_classes
        input_size = 224

        model_ft = model_ft.to(device)

        params_to_update = model_ft.parameters()
        if feature_extract:
            params_to_update = []
            for name, param in model_ft.named_parameters():
                if param.requires_grad == True:
                    params_to_update.append(param)
                    print("\t", name)
        else:
            for name, param in model_ft.named_parameters():
                if param.requires_grad == True:
                    print("\t", name)

        # Observe that all parameters are being optimized
        optimizer_ft = optim.SGD(params_to_update, lr=0.001, momentum=0.9)

        # Setup the loss fxn
        criterion = nn.CrossEntropyLoss()

        # Train and evaluate
        model_ft, hist = train_model(
            model_ft,
            dataloaders_dict,
            criterion,
            optimizer_ft,
            num_epochs=num_epochs,
            is_inception=(model_name == "inception"),
        )
        return model_ft
