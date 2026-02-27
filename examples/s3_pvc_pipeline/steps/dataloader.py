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
"""Data loading utilities for FashionMNIST."""

import warnings
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

# Suppress Lightning warnings about num_workers (intentionally 0 for Mac compatibility)
warnings.filterwarnings("ignore", message=".*does not have many workers.*")


class NumpyDirDataset(Dataset):
    """Dataset of .npy files under root/split/class_0/, class_1/, ... Labels from folder name."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.samples: list[tuple[Path, int]] = []
        for class_dir in sorted(self.data_dir.iterdir()):
            if not class_dir.is_dir() or not class_dir.name.startswith(
                "class_"
            ):
                continue
            label = int(class_dir.name.split("_", 1)[1])
            for path in sorted(class_dir.glob("*.npy")):
                self.samples.append((path, label))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        path, label = self.samples[idx]
        arr = np.load(path).astype(np.float32)
        # Already normalized; add channel dim (1, 28, 28) for Conv2d
        x = torch.from_numpy(arr).unsqueeze(0)
        return x, label


def get_dataloader(
    preprocessed_data_dir: str,
    batch_size: int,
    shuffle: bool = True,
) -> DataLoader:
    """Build a DataLoader from a single PVC directory path.

    preprocessed_path is a directory containing class_0/, class_1/, ... with .npy files
    (e.g. /mnt/data/v1/train or /mnt/data/v1/val).
    """
    dataset = NumpyDirDataset(preprocessed_data_dir)
    if len(dataset) == 0:
        raise ValueError(
            f"Dataset at '{preprocessed_data_dir}' has no samples (num_samples=0)."
        )
    return DataLoader(
        dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0
    )
