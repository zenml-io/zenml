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
"""Utility helpers for steps (e.g. FashionMNIST class names and visualization)."""

import random
from typing import List, Union

import matplotlib.pyplot as plt
import numpy as np

# FashionMNIST: class index -> class name
FASHION_MNIST_IDX_TO_CLASS_NAMES = {
    0: "T-shirt/top",
    1: "Trouser",
    2: "Pullover",
    3: "Dress",
    4: "Coat",
    5: "Sandal",
    6: "Shirt",
    7: "Sneaker",
    8: "Bag",
    9: "Ankle boot",
}

N_SAMPLE_IMAGES = 6
SAMPLE_PLOT_FIGSIZE = (12, 8)


def plot_sample_predictions(
    images: np.ndarray,
    actual_labels: Union[np.ndarray, List[int]],
    predicted_labels: Union[np.ndarray, List[int]],
    seed: int | None = None,
) -> plt.Figure:
    """Plot 6 random test images with actual and predicted labels.

    Uses FASHION_MNIST_IDX_TO_CLASS_NAMES for label display.

    Args:
        images: Array of shape (N, H, W) or (N, 1, H, W).
        actual_labels: Length-N array/list of true class indices (0-9).
        predicted_labels: Length-N array/list of predicted class indices.
        seed: Random seed for selecting indices (for reproducibility).

    Returns:
        matplotlib Figure (caller can save or show).
    """
    if seed is not None:
        random.seed(seed)

    N = len(images)
    if N == 0:
        raise ValueError("images must not be empty")
    n = min(N_SAMPLE_IMAGES, N)

    actual = np.asarray(actual_labels).ravel()
    pred = np.asarray(predicted_labels).ravel()
    if len(actual) != N or len(pred) != N:
        raise ValueError(
            "actual_labels and predicted_labels must have length N"
        )

    indices = random.sample(range(N), n)
    nrows, ncols = 2, 3

    fig, axes = plt.subplots(nrows, ncols, figsize=SAMPLE_PLOT_FIGSIZE)
    axes = np.atleast_2d(axes)
    for ax in axes.ravel():
        ax.axis("off")

    for i, idx in enumerate(indices):
        row, col = i // ncols, i % ncols
        ax = axes[row, col]

        img = images[idx]
        if img.ndim == 3 and img.shape[0] == 1:
            img = img[0]
        img = np.squeeze(img)
        # Scale to 0–1 for display (handles normalized or 0–255)
        vmin, vmax = img.min(), img.max()
        if vmax > vmin:
            img = (img.astype(np.float64) - vmin) / (vmax - vmin)
        else:
            img = np.clip(img.astype(np.float64), 0, 1)
        ax.imshow(img, cmap="gray")
        a, p = int(actual[idx]), int(pred[idx])
        actual_name = FASHION_MNIST_IDX_TO_CLASS_NAMES.get(a, str(a))
        pred_name = FASHION_MNIST_IDX_TO_CLASS_NAMES.get(p, str(p))
        correct = "✓" if a == p else "✗"
        ax.set_title(
            f"Actual: {actual_name}\nPred: {pred_name} {correct}", fontsize=9
        )
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    return fig
