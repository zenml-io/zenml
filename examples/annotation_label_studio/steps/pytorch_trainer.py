import os
import tempfile
import time
from copy import deepcopy
from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from torchvision import models, transforms

from zenml.io import fileio
from zenml.steps import step
from zenml.steps.step_context import StepContext
from zenml.utils import io_utils

PIPELINE_NAME = "training_pipeline"  # TODO: cleanup
PIPELINE_STEP_NAME = "model_trainer"  # TODO: cleanup


def train_model(
    model,
    dataloaders,
    criterion,
    optimizer,
    num_epochs=25,
    device="cpu",
):
    since = time.time()

    val_acc_history = []

    best_model_wts = deepcopy(model.state_dict())
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
                best_model_wts = deepcopy(model.state_dict())
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


class CustomDataset:
    def __init__(self, image_urls, labels, transforms) -> None:
        assert len(image_urls) == len(labels)
        self.transforms = transforms

        # Download all images from the artifact store as np.ndarray
        self.images = []
        temp_dir = tempfile.TemporaryDirectory()
        for i, image_url in enumerate(image_urls):
            parts = image_url.split("/")
            az_url = "az://" + "/".join(parts[3:])  # TODO: other providers?
            path = os.path.join(temp_dir.name, f"{i}.jpeg")
            io_utils.copy(az_url, path)
            with fileio.open(path, "rb") as f:
                image = np.asarray(Image.open(f))
                self.images.append(image)
        fileio.rmtree(temp_dir.name)

        # Define class-label mapping and map labels
        self.class_label_mapping = {"aria": 0, "not_aria": 1}  # TODO
        self.labels = [self.class_label_mapping[label] for label in labels]

    def __getitem__(self, idx):
        image = self.transforms(self.images[idx])
        label = self.labels[idx]
        return (image, label)

    def __len__(self):
        return len(self.images)


def _find_last_successful_run(context: StepContext) -> int:
    """Get the index of the last successful run of this pipeline and step."""
    pipeline = context.metadata_store.get_pipeline(PIPELINE_NAME)
    if pipeline is not None:
        for idx, run in reversed(list(enumerate(pipeline.runs))):
            try:
                run.get_step(PIPELINE_STEP_NAME).output.read()
                return idx
            except (KeyError, ValueError):  # step didn't run or had no output
                pass
    return None


def _load_last_model(context: StepContext) -> nn.Module:
    """Return the most recently trained model from this pipeline, or None."""
    idx = _find_last_successful_run(context=context)
    if idx is None:
        return None
    last_run = context.metadata_store.get_pipeline(PIPELINE_NAME).runs[idx]
    return last_run.get_step(PIPELINE_STEP_NAME).output.read()


def _is_new_data_available(
    image_urls: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> bool:
    """Find whether new data is available since the last run."""
    # If there are no samples, nothing can be new.
    num_samples = len(image_urls)
    if num_samples == 0:
        return False

    # Otherwise, if there was no previous run, the data is for sure new.
    idx = _find_last_successful_run(context=context)    
    if idx is None:
        return True

    # Else, we check whether we had the same number of samples before.
    last_run = context.metadata_store.get_pipeline(PIPELINE_NAME).runs[idx]
    last_inputs = last_run.get_step(PIPELINE_STEP_NAME).inputs
    last_image_urls = last_inputs["image_urls"].read()
    return len(last_image_urls) != len(image_urls)


def load_pretrained_mobilenetv3(num_classes : int = 2):
    """Load a pretrained mobilenetv3 with fresh classification head."""
    model = models.mobilenet_v3_small(pretrained=True)
    for param in model.parameters():
        param.requires_grad = False
    model.classifier = nn.Linear(576, num_classes)
    model.num_classes = num_classes
    return model


def load_mobilenetv3_transforms():
    """Load the transforms required before running mobilenetv3 on data."""
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    return transforms.Compose([transforms.ToTensor(), weights.transforms()])


@step(enable_cache=False)
def pytorch_model_trainer(
    image_urls: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> nn.Module:

    # Try to load a model from a previous run, otherwise use a pretrained net
    model = _load_last_model(context=context)
    if model is None:
        model = load_pretrained_mobilenetv3()

    # If there is no new data, just return the model
    if not _is_new_data_available(image_urls, labels, context):
        return model

    # Otherwise finetune the model on the current data
    # TODO: below to step config
    batch_size = 1
    num_epochs = 1
    device = "cpu"
    shuffle = True
    num_workers = 1

    # Write images and labels to torch dataset
    dataset = CustomDataset(
        image_urls=image_urls,
        labels=labels,
        transforms=load_mobilenetv3_transforms(),
    )

    # Create training and validation dataloaders
    dataloaders_dict = {
        x: torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
        )
        for x in ["train", "val"]
    }

    # Define optimizer
    optimizer_ft = optim.Adam(params=model.classifier.parameters())

    # Define loss
    criterion = nn.CrossEntropyLoss()

    # Train and evaluate
    model, hist = train_model(
        model,
        dataloaders_dict,
        criterion,
        optimizer_ft,
        num_epochs=num_epochs,
        device=device,
    )
    return model
