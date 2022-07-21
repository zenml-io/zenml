import os
import time
from copy import deepcopy
from typing import Dict, List

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms

from zenml.steps import step
from zenml.steps.step_context import StepContext


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
    else:
        pass  # TODO

    # If there is no new data, just return the model
    if not image_urls or not labels:
        return model

    # Otherwise train the model on the new data
    data_dir = ""  # TODO
    batch_size = 1  # TODO: to step config
    num_epochs = 5  # TODO: to step config
    input_size = 224  # TODO: to step config
    device = "cpu"  # TODO: to step config

    model = model.to(device)

    # Define Transforms
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    data_transforms = {
        "train": transforms.Compose(
            [
                transforms.RandomResizedCrop(input_size),
                transforms.RandomHorizontalFlip(),
                weights.transforms(),
            ]
        ),
        "val": transforms.Compose(
            [
                transforms.Resize(input_size),
                transforms.CenterCrop(input_size),
                weights.transforms(),
            ]
        ),
    }

    # Create training and validation datasets
    image_datasets = {
        x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
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

    # Define optimizer
    optimizer_ft = optim.Adam(params=model.classifier.parameters)

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
