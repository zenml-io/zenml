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
            az_url = "az://" + "/".join(parts[3:])
            path = os.path.join(temp_dir.name, f"{i}.jpeg")
            io_utils.copy(az_url, path)
            with fileio.open(path, "rb") as f:
                image = np.asarray(Image.open(f))
                self.images.append(image)
        fileio.rmtree(temp_dir.name)

        # Define class-label mapping and map labels

        self.class_label_mapping = {"aria": 0, "not_aria": 1}
        self.labels = [self.class_label_mapping[label] for label in labels]

    def __getitem__(self, idx):
        image = self.transforms(self.images[idx])
        label = self.labels[idx]
        return (image, label)

    def __len__(self):
        return len(self.images)


@step(enable_cache=False)
def pytorch_model_trainer(
    image_urls: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> nn.Module:

    num_classes = 2  # TODO: to step config

    # If this is the first run, load a pretrained MobileNetv3
    if not labels or not image_urls:
        model = models.mobilenet_v3_small(pretrained=True)
        for param in model.parameters():
            param.requires_grad = False
        model.classifier = nn.Linear(576, num_classes)
        model.num_classes = num_classes
        return model

    # Otherwise load the model from the previous run
    train_run = context.metadata_store.get_pipeline(PIPELINE_NAME).runs[
        -1
    ]  # TODO
    model = train_run.get_step(PIPELINE_STEP_NAME).output.read()

    # If there is no new data, just return the model - TODO

    # Otherwise train the model on the new data
    batch_size = 1  # TODO: to step config
    num_epochs = 5  # TODO: to step config
    input_size = 224  # TODO: to step config
    device = "cpu"  # TODO: to step config
    model = model.to(device)  # TODO: need to pass back to CPU?

    # Define Transforms
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    preprocessing = transforms.Compose(
        [
            transforms.ToTensor(),
            weights.transforms(),
        ]
    )

    # Write images and labels to torch datasets
    dataset = CustomDataset(
        image_urls=image_urls, labels=labels, transforms=preprocessing
    )

    breakpoint()

    # Create training and validation datasets
    image_datasets = {
        "train": dataset,
        "val": dataset,
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
