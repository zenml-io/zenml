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

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.transforms import ToTensor

from zenml.integrations.constants import PYTORCH
from zenml.pipelines import pipeline
from zenml.steps import Output, step

# Get cpu or gpu device for training.
device = "cuda" if torch.cuda.is_available() else "cpu"


# Define model
class NeuralNetwork(nn.Module):
    def __init__(self):
        super(NeuralNetwork, self).__init__()
        self.flatten = nn.Flatten()
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(28 * 28, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 10),
        )

    def forward(self, x):
        x = self.flatten(x)
        logits = self.linear_relu_stack(x)
        return logits


@step
def importer_mnist() -> Output(
    train_dataloader=DataLoader,
    test_dataloader=DataLoader,
):
    """Download the Fashion MNIST dataset."""
    # Download training data from open datasets.
    training_data = datasets.FashionMNIST(
        root="data",
        train=True,
        download=True,
        transform=ToTensor(),
    )

    # Download test data from open datasets.
    test_data = datasets.FashionMNIST(
        root="data",
        train=False,
        download=True,
        transform=ToTensor(),
    )
    batch_size = 64

    # Create dataloaders.
    train_dataloader = DataLoader(training_data, batch_size=batch_size)
    test_dataloader = DataLoader(test_data, batch_size=batch_size)

    return train_dataloader, test_dataloader


@step
def trainer(train_dataloader: DataLoader) -> nn.Module:
    """Trains on the train dataloader"""
    model = NeuralNetwork().to(device)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-3)
    size = len(train_dataloader.dataset)
    model.train()
    for batch, (X, y) in enumerate(train_dataloader):
        X, y = X.to(device), y.to(device)

        # Compute prediction error
        pred = model(X)
        loss = loss_fn(pred, y)

        # Backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch % 100 == 0:
            loss, current = loss.item(), batch * len(X)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")
    return model


@step
def evaluator(test_dataloader: DataLoader, model: nn.Module) -> float:
    """Evaluates on the model."""
    loss_fn = nn.CrossEntropyLoss()

    size = len(test_dataloader.dataset)
    num_batches = len(test_dataloader)
    model.eval()
    test_loss, correct = 0, 0
    with torch.no_grad():
        for X, y in test_dataloader:
            X, y = X.to(device), y.to(device)
            pred = model(X)
            test_loss += loss_fn(pred, y).item()
            correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    test_loss /= num_batches
    correct /= size
    print(
        f"Test Error: \n Accuracy: {(100*correct):>0.1f}%, Avg loss: {test_loss:>8f} \n"
    )
    return 100 * correct


# Define the pipeline
@pipeline(required_integrations=[PYTORCH])
def fashion_mnist_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Link all the steps and artifacts together"""
    train_dataloader, test_dataloader = importer()
    model = trainer(train_dataloader)
    evaluator(test_dataloader=test_dataloader, model=model)


if __name__ == "__main__":
    # Initialize a pipeline run
    p = fashion_mnist_pipeline(
        importer=importer_mnist(),
        trainer=trainer(),
        evaluator=evaluator(),
    )

    # Run the pipeline
    p.run()
