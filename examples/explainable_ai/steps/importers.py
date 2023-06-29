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

from torch.utils.data import DataLoader
from torchvision import datasets
import torchvision

from zenml import step
from zenml.steps import Output


def load_model():
    """Load pre-trained model from torchvision hub."""
    weights = torchvision.models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
    model = torchvision.models.mobilenet_v3_small(weights=weights)
    categories = weights.meta["categories"]
    transform = weights.transforms()
    return model, categories, transform

@step
def importer_cifa10() -> (
    Output(
        train_dataloader=DataLoader,
        test_dataloader=DataLoader,
    )
):
    """Download the CIFAR10 dataset."""
    # Download training data from open datasets.
    _, _, transform = load_model()
    training_data = datasets.CIFAR10(
        root="data",
        train=True,
        download=True,
        transform=transform,
    )

    # Download test data from open datasets.
    test_data = datasets.CIFAR10(
        root="data",
        train=False,
        download=True,
        transform=transform,
    )
    batch_size = 1

    # Create dataloaders.
    train_dataloader = DataLoader(training_data, batch_size=batch_size)
    test_dataloader = DataLoader(test_data, batch_size=batch_size)

    return train_dataloader, test_dataloader
