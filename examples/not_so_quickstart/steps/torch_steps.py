#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.


import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader, TensorDataset

from zenml.steps import step

from .params import TrainerConfig

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Net(nn.Module):
    """Straightforward NN for classification."""

    def __init__(self):
        super(Net, self).__init__()
        self.flat_network = nn.Sequential(
            nn.Flatten(),
            nn.Linear(784, 10),
        )
        # fully connected layer, output 10 classes
        self.out = nn.Linear(10, 10)

    def forward(self, x):
        x = self.flat_network(x)
        x = self.out(x)
        output = self.out(x)
        return output


def get_data_loader_from_np(X: np.ndarray, y: np.ndarray) -> DataLoader:
    """Returns a torch Dataloader from two np arrays."""
    tensor_x = torch.Tensor(X)  # transform to torch tensor
    tensor_y = torch.Tensor(y).type(torch.LongTensor)

    torch_dataset = TensorDataset(tensor_x, tensor_y)  # create your datset
    torch_dataloader = DataLoader(torch_dataset)  # create your dataloader
    return torch_dataloader


@step
def torch_trainer(
    config: TrainerConfig,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> nn.Module:
    """Train a neural net from scratch to recognise MNIST digits return our
    model or the learner"""
    train_loader = get_data_loader_from_np(X_train, y_train)

    model = Net().to(DEVICE)
    optimizer = optim.Adadelta(model.parameters(), lr=config.lr)

    scheduler = StepLR(optimizer, step_size=1, gamma=config.gamma)
    for epoch in range(1, config.epochs + 1):
        model.train()
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(DEVICE), target.to(DEVICE)
            optimizer.zero_grad()
            output = model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            optimizer.step()
        scheduler.step()

    return model


@step
def torch_evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: nn.Module,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""
    model.eval()
    test_loader = get_data_loader_from_np(X_test, y_test)
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(DEVICE), target.to(DEVICE)
            output = model(data)
            test_loss += F.nll_loss(
                output, target, reduction="sum"
            ).item()  # sum up batch loss
            pred = output.argmax(
                dim=1, keepdim=True
            )  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)

    print(
        "\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n".format(
            test_loss,
            correct,
            len(test_loader.dataset),
            100.0 * correct / len(test_loader.dataset),
        )
    )
    return 100.0 * correct / len(test_loader.dataset)
