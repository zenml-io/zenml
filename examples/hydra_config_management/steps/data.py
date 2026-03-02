# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Shared data loading utilities for the Hydra config management example."""

import tempfile
import warnings
from typing import Tuple

import filelock

# Suppress Lightning warnings about num_workers (intentionally 0 for Mac compatibility)
warnings.filterwarnings("ignore", message=".*does not have many workers.*")

import torch
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
from torchvision.datasets import FashionMNIST


def get_fashion_mnist_loaders(
    batch_size: int,
    seed: int = 42,
) -> Tuple[DataLoader, DataLoader]:
    """Load FashionMNIST and return train/val DataLoaders.

    Uses an 80/20 train/val split with a fixed seed for reproducibility.
    Dataset is downloaded to a temporary directory.

    Args:
        batch_size: Batch size for the training DataLoader.
        seed: Random seed for the train/val split.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
        ]
    )

    data_dir = f"{tempfile.gettempdir()}/data"

    lock_path = f"{data_dir}/fashion_mnist.lock"
    with filelock.FileLock(lock_path):
        full_dataset = FashionMNIST(
            root=data_dir, train=True, download=True, transform=transform
        )

    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(
        full_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(seed),
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=256, shuffle=False, num_workers=0
    )

    return train_loader, val_loader
