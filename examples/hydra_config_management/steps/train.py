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
"""Training step for the Hydra config management example."""

from typing import Annotated

from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import EarlyStopping

from steps.data import get_fashion_mnist_loaders
from steps.model import FashionMNISTClassifier
from zenml import log_metadata, step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            gpu_count=0,  # Set to 1 for GPU training
            memory="4GB",
        )
    }
)
def train_model(
    learning_rate: float = 0.001,
    batch_size: int = 64,
    hidden_dim: int = 32,
    max_epochs: int = 10,
) -> Annotated[LightningModule, "trained_model"]:
    """Train a CNN on FashionMNIST with Hydra-configured hyperparameters.

    All hyperparameters are passed explicitly from the Hydra config,
    making the training fully configurable from YAML and CLI overrides.

    Args:
        learning_rate: Learning rate for the Adam optimizer
        batch_size: Training batch size
        hidden_dim: Number of filters in the first conv layer
        max_epochs: Maximum number of training epochs

    Returns:
        Trained Lightning model saved as a ZenML artifact
    """
    print("\n🚀 Training FashionMNIST classifier")
    print(f"   learning_rate={learning_rate:.6f}")
    print(f"   batch_size={batch_size}")
    print(f"   hidden_dim={hidden_dim}")
    print(f"   max_epochs={max_epochs}")

    print("   Loading FashionMNIST dataset...")
    train_loader, val_loader = get_fashion_mnist_loaders(batch_size=batch_size)
    print(
        f"   Train samples: {len(train_loader.dataset)}, "
        f"Val samples: {len(val_loader.dataset)}"
    )

    model = FashionMNISTClassifier(
        learning_rate=learning_rate,
        hidden_dim=hidden_dim,
    )

    trainer = Trainer(
        max_epochs=max_epochs,
        accelerator="auto",
        devices=1,
        callbacks=[
            EarlyStopping(
                monitor="val_loss",
                patience=10,
                mode="min",
            )
        ],
        enable_checkpointing=False,
        enable_progress_bar=False,
        logger=False,
        deterministic=True,
    )

    print(f"   Training for up to {max_epochs} epochs...")
    trainer.fit(model, train_loader, val_loader)

    val_loss = float(trainer.callback_metrics.get("val_loss", 0.0))
    val_accuracy = float(trainer.callback_metrics.get("val_acc", 0.0)) * 100
    train_accuracy = (
        float(trainer.callback_metrics.get("train_acc", 0.0)) * 100
    )

    print(f"   Training epochs: {trainer.current_epoch + 1}")
    print(
        f"   Final validation: loss={val_loss:.4f}, accuracy={val_accuracy:.2f}%"
    )
    print(f"   Final training: accuracy={train_accuracy:.2f}%")
    print("✅ Training complete\n")

    log_metadata(
        metadata={
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "train_accuracy": train_accuracy,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "hidden_dim": hidden_dim,
            "n_epochs": trainer.current_epoch + 1,
            "max_epochs": max_epochs,
            "converged": trainer.current_epoch + 1 < max_epochs,
        },
        infer_artifact=True,
    )

    return model
