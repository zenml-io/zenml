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
"""Training step for individual Optuna trials using PyTorch Lightning."""

import warnings
from typing import Annotated, Any, Dict

import torch
from lightning import Trainer
from lightning.pytorch.callbacks import EarlyStopping
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
from torchvision.datasets import FashionMNIST

from steps.model import FashionMNISTClassifier
from zenml import log_metadata, step
from zenml.config import ResourceSettings

# Suppress Lightning warnings about num_workers (intentionally 0 for Mac compatibility)
warnings.filterwarnings("ignore", message=".*does not have many workers.*")


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            gpu_count=0,  # Set to 1 for GPU training
            memory="4GB",
        )
    }
)
def train_trial(
    trial_config: Dict[str, Any],
    max_iter: int = 10,
) -> Annotated[Dict[str, Any], "trial_result"]:
    """Train a single trial with PyTorch Lightning.

    This step trains a CNN on FashionMNIST using the hyperparameters
    from the trial configuration. Training happens in isolation,
    allowing parallel execution across multiple trials.

    Args:
        trial_config: Trial configuration containing:
            - trial_number: Optuna trial ID
            - learning_rate: Learning rate for optimizer
            - batch_size: Training batch size
            - hidden_dim: Number of filters in conv layers
        max_iter: Maximum number of training epochs (default: 10)

    Returns:
        Dictionary containing trial results:
        - trial_number: Trial ID for reporting back to Optuna
        - val_loss: Validation loss (optimization metric)
        - val_accuracy: Validation accuracy
        - learning_rate, batch_size, hidden_dim: Hyperparameters used

    Example:
        >>> config = {"trial_number": 0, "learning_rate": 0.001, "batch_size": 64, "hidden_dim": 32}
        >>> result = train_trial(config)
        >>> print(result["val_loss"])
        0.432
    """
    trial_number = trial_config["trial_number"]
    learning_rate = trial_config["learning_rate"]
    batch_size = trial_config["batch_size"]
    hidden_dim = trial_config["hidden_dim"]

    print(f"\n🚀 Training Trial {trial_number}")
    print(
        f"   learning_rate={learning_rate:.6f}, batch_size={batch_size}, hidden_dim={hidden_dim}"
    )

    # Load FashionMNIST dataset
    print("   Loading FashionMNIST dataset...")
    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),  # Normalize to [-1, 1]
        ]
    )

    full_dataset = FashionMNIST(
        root="/tmp/data", train=True, download=True, transform=transform
    )

    # Split into train and validation (80/20 split with fixed seed)
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(
        full_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=256, shuffle=False, num_workers=0
    )

    print(
        f"   Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}"
    )

    # Build and train model
    model = FashionMNISTClassifier(
        learning_rate=learning_rate,
        hidden_dim=hidden_dim,
    )

    # Configure trainer
    trainer = Trainer(
        max_epochs=max_iter,
        accelerator="cpu",  # Use CPU (MPS can hang on Mac)
        devices=1,
        callbacks=[
            EarlyStopping(
                monitor="val_loss",
                patience=10,
                mode="min",
            )
        ],
        enable_progress_bar=False,
        logger=False,
        deterministic=True,
    )

    print(f"   Training for up to {max_iter} epochs...")
    trainer.fit(model, train_loader, val_loader)

    # Get final metrics
    val_loss = float(trainer.callback_metrics.get("val_loss", 0.0))
    val_accuracy = float(trainer.callback_metrics.get("val_acc", 0.0)) * 100

    print(f"   Training epochs: {trainer.current_epoch + 1}")
    print(f"   Validation: loss={val_loss:.4f}, accuracy={val_accuracy:.2f}%")
    print(f"✅ Trial {trial_number} complete\n")

    # Prepare result
    result = {
        "trial_number": trial_number,
        "val_loss": val_loss,
        "val_accuracy": val_accuracy,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "hidden_dim": hidden_dim,
        "n_epochs": trainer.current_epoch + 1,
        "max_epochs": max_iter,
    }

    # Log metadata for dashboard visibility and MCP server queries
    log_metadata(
        metadata={
            "trial_number": trial_number,
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "hidden_dim": hidden_dim,
            "n_epochs": trainer.current_epoch + 1,
        },
        artifact_name="trial_result",
        infer_artifact=True,
    )

    return result
