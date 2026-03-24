#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""PyTorch CNN training step on GPU."""

import subprocess
from typing import Dict

import torch
import torch.nn as nn
import torch.optim as optim

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


def _log_nvidia_smi(label: str = "") -> None:
    """Run nvidia-smi and log the output for GPU visibility during demos."""
    prefix = f"[{label}] " if label else ""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("%snvidia-smi output:\n%s", prefix, result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

# Synthetic dataset dimensions — large enough to keep the GPU busy.
_NUM_SAMPLES = 2048
_IMAGE_CHANNELS = 3
_IMAGE_SIZE = 64
_NUM_CLASSES = 10


class _SimpleCNN(nn.Module):
    """Minimal CNN: two conv blocks + two FC layers."""

    def __init__(self, num_classes: int = _NUM_CLASSES) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(_IMAGE_CHANNELS, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        # After two MaxPool2d(2) on a 64×64 image: 64 × 16 × 16
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 16 * 16, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        """Forward pass.

        Args:
            x: Input tensor of shape (N, C, H, W).

        Returns:
            Logits tensor of shape (N, num_classes).
        """
        return self.classifier(self.features(x))


def _cleanup_gpu() -> None:
    """Free GPU memory caches if CUDA is available."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


@step
def pytorch_cnn_train(
    epochs: int = 5,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
) -> Dict[str, float]:
    """Train a simple CNN on synthetic image data using GPU acceleration.

    Generates a random dataset in memory (no download required) and trains
    for the specified number of epochs. Logs per-epoch loss metadata so the
    ZenML dashboard shows training progress.

    Args:
        epochs: Number of full passes over the synthetic dataset.
        batch_size: Mini-batch size for each gradient update.
        learning_rate: Adam optimizer learning rate.

    Returns:
        Dict with final_loss, best_loss, and total_samples_seen.
    """
    _log_nvidia_smi("before training")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        logger.info(
            "Training on GPU: %s", torch.cuda.get_device_name(0)
        )
    else:
        logger.warning(
            "No CUDA GPU found — training on CPU. "
            "Expect significantly slower throughput."
        )

    try:
        model = _SimpleCNN(num_classes=_NUM_CLASSES).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)

        # Synthetic dataset — keeps the demo self-contained (no downloads).
        x = torch.randn(
            _NUM_SAMPLES, _IMAGE_CHANNELS, _IMAGE_SIZE, _IMAGE_SIZE,
            device=device,
        )
        y = torch.randint(0, _NUM_CLASSES, (_NUM_SAMPLES,), device=device)

        steps_per_epoch = _NUM_SAMPLES // batch_size
        epoch_losses = []

        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            for i in range(steps_per_epoch):
                start = i * batch_size
                end = start + batch_size
                xb, yb = x[start:end], y[start:end]

                optimizer.zero_grad()
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            avg_loss = epoch_loss / steps_per_epoch
            epoch_losses.append(avg_loss)
            logger.info("Epoch [%d/%d] — avg loss: %.4f", epoch + 1, epochs, avg_loss)
            _log_nvidia_smi(f"epoch {epoch + 1}/{epochs}")
            log_metadata(
                metadata={"training": {f"epoch_{epoch + 1}_loss": round(avg_loss, 6)}}
            )

        final_loss = epoch_losses[-1]
        best_loss = min(epoch_losses)
        total_samples = epochs * _NUM_SAMPLES

        log_metadata(
            metadata={
                "training": {
                    "final_loss": round(final_loss, 6),
                    "best_loss": round(best_loss, 6),
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    "total_samples_seen": total_samples,
                    "device": device.type,
                }
            }
        )
        return {
            "final_loss": final_loss,
            "best_loss": best_loss,
            "total_samples_seen": float(total_samples),
        }

    finally:
        _cleanup_gpu()
