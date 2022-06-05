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


import logging
import os

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
from mnist import Net
from torch.utils.data import DataLoader

from zenml.integrations.constants import KSERVE, PYTORCH
from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig

logger = logging.getLogger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")


def data_loader(
    train_set: bool = True, batch_size: int = 4, shuffle: bool = True
) -> DataLoader:
    """Returns a torch Dataloader from two np arrays."""
    data_loader = torch.utils.data.DataLoader(
        torchvision.datasets.MNIST(
            "mnist/data",
            train=train_set,
            download=True,
            transform=torchvision.transforms.Compose(
                [
                    torchvision.transforms.ToTensor(),
                    torchvision.transforms.Normalize((0.1307,), (0.3081,)),
                ]
            ),
        ),
        batch_size=batch_size,
        shuffle=shuffle,
    )
    return data_loader


class TrainerConfig(BaseStepConfig):
    """Trainer params"""

    batch_size: int = 4
    epochs: int = 2
    lr: float = 0.01
    momentum: float = 0.5
    shuffle: bool = True


@step()
def torch_trainer(
    config: TrainerConfig,
) -> nn.Module:
    """Train a neural net from scratch to recognize MNIST digits return our
    model or the learner"""
    train_loader = data_loader(
        train_set=True, batch_size=config.batch_size, shuffle=config.shuffle
    )

    model = Net().to(DEVICE)
    optimizer = optim.SGD(
        model.parameters(), lr=config.lr, momentum=config.momentum
    )

    for epoch in range(1, config.epochs + 1):
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


class EvaluatorConfig(BaseStepConfig):
    """Trainer params"""

    batch_size: int = 4
    shuffle: bool = True


@step
def torch_evaluator(
    config: EvaluatorConfig,
    model: nn.Module,
) -> float:
    """Calculate the loss for the model for each epoch in a graph"""
    model.eval()
    test_loader = data_loader(
        train_set=False, batch_size=config.batch_size, shuffle=config.shuffle
    )
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
    return correct / len(test_loader.dataset)


class DeploymentTriggerConfig(BaseStepConfig):
    """Parameters that are used to trigger the deployment"""

    min_accuracy: float


@step
def deployment_trigger(
    accuracy: float,
    config: DeploymentTriggerConfig,
) -> bool:
    """Implements a simple model deployment trigger that looks at the
    input model accuracy and decides if it is good enough to deploy"""

    return accuracy > config.min_accuracy


# Define the pipeline
@pipeline(
    enable_cache=True,
    required_integrations=[KSERVE, PYTORCH],
    requirements_file=requirements_file,
)
def kserve_pytorch_deployment_pipeline(
    trainer,
    evaluator,
    deployment_trigger,
    custom_model_deployer,
):
    # Link all the steps artifacts together
    model = trainer()
    accuracy = evaluator(model=model)
    deployment_decision = deployment_trigger(accuracy=accuracy)
    custom_model_deployer(
        deployment_decision,
        model,
    )
