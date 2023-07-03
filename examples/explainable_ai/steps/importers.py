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

from typing import List

import torch
import torchvision
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets

from zenml import step
from zenml.steps import Output


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.conv_layers = nn.Sequential(
            nn.Conv2d(1, 10, kernel_size=5),
            nn.MaxPool2d(2),
            nn.ReLU(),
            nn.Conv2d(10, 20, kernel_size=5),
            nn.Dropout(),
            nn.MaxPool2d(2),
            nn.ReLU(),
        )
        self.fc_layers = nn.Sequential(
            nn.Linear(320, 50),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(50, 10),
            nn.Softmax(dim=1),
        )

    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(-1, 320)
        x = self.fc_layers(x)
        return x


def load_model():
    """Create new model."""
    model = Net()
    transform = torchvision.transforms.ToTensor()
    return model, list(range(0, 10)), transform


@step
def importer_MNIST(
    batch_size: int,
) -> Output(
    train_dataloader=DataLoader,
    test_dataloader=DataLoader,
    val_dataloader=DataLoader,
    classes=List,
):
    """Download the MNIST dataset."""
    # Download training data from open datasets.
    _, _, transform = load_model()
    training_data = datasets.MNIST(
        root="data",
        train=True,
        download=True,
        transform=transform,
    )

    # Download test data from open datasets.
    test_data = datasets.MNIST(
        root="data",
        train=False,
        download=True,
        transform=transform,
    )

    train_size = int(0.8 * len(training_data))
    val_size = len(training_data) - train_size
    training_data, validation_data = torch.utils.data.random_split(
        training_data,
        [train_size, val_size],
    )

    classes: List[str] = [str(x) for x in range(0, 10)]

    # Create dataloaders.
    train_dataloader = DataLoader(
        training_data, batch_size=batch_size, shuffle=True
    )
    val_dataloader = DataLoader(validation_data, batch_size=batch_size)
    test_dataloader = DataLoader(test_data, batch_size=batch_size)

    return train_dataloader, test_dataloader, val_dataloader, classes
