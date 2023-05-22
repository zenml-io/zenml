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
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from rich import print
from torch.utils.data import DataLoader

from zenml import step
from zenml.steps import BaseParameters

from .pytorch_net import Net

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class PytorchTrainerParameters(BaseParameters):
    """Trainer params."""

    epochs: int = 2
    lr: float = 0.01
    momentum: float = 0.5


@step
def pytorch_trainer(
    params: PytorchTrainerParameters, train_loader: DataLoader
) -> nn.Module:
    """Train a neural net from scratch to recognize MNIST digits.

    This returns our model or the learner.

    Args:
        params: The parameters for the trainer.
        train_loader: The training data.

    Returns:
        The trained model.
    """
    model = Net().to(DEVICE)
    optimizer = optim.Adadelta(model.parameters(), lr=params.lr)

    for epoch in range(1, params.epochs + 1):
        model.train()
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(DEVICE), target.to(DEVICE)
            optimizer.zero_grad()
            output = model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            optimizer.step()
        print("Train Epoch: {} \tLoss: {:.6f}".format(epoch, loss.item()))

    return model
