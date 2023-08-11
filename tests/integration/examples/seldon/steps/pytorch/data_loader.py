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


from typing import Tuple

import torchvision
from torch.utils.data import DataLoader
from typing_extensions import Annotated

from zenml import step


def build_data_loader(
    is_train: bool = True, batch_size: int = 4, shuffle: bool = True
) -> DataLoader:
    """Returns a torch Dataloader from two np arrays."""
    data_loader = DataLoader(
        torchvision.datasets.MNIST(
            "mnist/data",
            train=is_train,
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


@step
def pytorch_data_loader(
    train_shuffle: bool = True,
    train_batch_size: int = 4,
    test_batch_size: int = 4,
    test_shuffle: bool = True,
) -> Tuple[
    Annotated[DataLoader, "train_loader"],
    Annotated[DataLoader, "test_loader"],
]:
    train_loader = build_data_loader(
        is_train=True,
        batch_size=train_batch_size,
        shuffle=train_shuffle,
    )
    test_loader = build_data_loader(
        is_train=False,
        batch_size=test_batch_size,
        shuffle=test_shuffle,
    )
    return train_loader, test_loader
