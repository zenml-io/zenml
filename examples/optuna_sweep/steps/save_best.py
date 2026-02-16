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
"""Step to retrain and save the best model from hyperparameter sweep."""

import warnings
from typing import Annotated, Any, Dict

import torch
from lightning import LightningModule, Trainer
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
from torchvision.datasets import FashionMNIST

from zenml import log_metadata, step
from zenml.config import ResourceSettings

# Suppress Lightning warnings about num_workers (intentionally 0 for Mac compatibility)
warnings.filterwarnings("ignore", message=".*does not have many workers.*")


class FashionMNISTClassifier(LightningModule):
    """Simple CNN for FashionMNIST classification."""

    def __init__(self, learning_rate: float, hidden_dim: int):
        super().__init__()
        self.save_hyperparameters()
        self.learning_rate = learning_rate

        self.model = torch.nn.Sequential(
            torch.nn.Conv2d(1, hidden_dim, kernel_size=3, padding=1),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),
            torch.nn.Conv2d(
                hidden_dim, hidden_dim * 2, kernel_size=3, padding=1
            ),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(2),
            torch.nn.Flatten(),
            torch.nn.Linear(hidden_dim * 2 * 7 * 7, 64),  # Smaller FC layer
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(64, 10),
        )
        self.loss_fn = torch.nn.CrossEntropyLoss()

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.loss_fn(logits, y)
        acc = (logits.argmax(1) == y).float().mean()
        self.log("train_loss", loss, prog_bar=True)
        self.log("train_acc", acc, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.loss_fn(logits, y)
        acc = (logits.argmax(1) == y).float().mean()
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", acc, prog_bar=True)
        return {"val_loss": loss, "val_acc": acc}

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.learning_rate)


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            gpu_count=0,  # Set to 1 for GPU training
            memory="4GB",
        )
    }
)
def retrain_best_model(
    sweep_summary: Dict[str, Any],
    max_iter: int = 20,
) -> Annotated[Any, "best_model"]:
    """Retrain the best model from hyperparameter sweep for production.

    This step identifies the best trial from the sweep results, then
    retrains a model with those hyperparameters using more epochs
    for better convergence. The final model is saved as a ZenML artifact.

    Args:
        sweep_summary: Summary from report_results containing best_params
        max_iter: Maximum training epochs for final model (default: 200,
            higher than sweep trials for better convergence)

    Returns:
        Trained Lightning model with best hyperparameters, ready for
        production use

    Example:
        >>> summary = {"best_params": {"learning_rate": 0.001, ...}}
        >>> model = retrain_best_model(summary, max_iter=200)
    """
    best_params = sweep_summary["best_params"]
    best_val_loss = sweep_summary["best_val_loss"]
    best_trial_number = sweep_summary["best_trial_number"]

    print("\n🏆 Retraining best model for production")
    print(f"   Best trial: {best_trial_number}")
    print(f"   Best validation loss: {best_val_loss:.4f}")
    print("   Hyperparameters:")
    for key, value in best_params.items():
        print(f"      {key}: {value}")
    print(f"   Training for {max_iter} epochs (more than sweep trials)")

    # Extract hyperparameters
    learning_rate = best_params["learning_rate"]
    batch_size = best_params["batch_size"]
    hidden_dim = best_params["hidden_dim"]

    # Load FashionMNIST dataset
    print("   Loading FashionMNIST dataset...")
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))]
    )

    full_dataset = FashionMNIST(
        root="/tmp/data", train=True, download=True, transform=transform
    )

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

    # Build model with best hyperparameters
    model = FashionMNISTClassifier(
        learning_rate=learning_rate,
        hidden_dim=hidden_dim,
    )

    # Configure trainer with early stopping for production
    trainer = Trainer(
        max_epochs=max_iter,
        accelerator="cpu",  # Use CPU (MPS can hang on Mac)
        devices=1,
        callbacks=[
            EarlyStopping(
                monitor="val_loss",
                patience=15,  # More patience for production
                mode="min",
            ),
            ModelCheckpoint(
                monitor="val_loss",
                mode="min",
                save_top_k=1,
            ),
        ],
        enable_progress_bar=False,
        logger=False,
        deterministic=True,
    )

    # Train the production model
    print(f"   Training production model (up to {max_iter} epochs)...")
    trainer.fit(model, train_loader, val_loader)

    # Get final metrics
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
    print("✅ Production model trained and ready\n")

    # Log metadata on the model artifact
    log_metadata(
        metadata={
            "source": "hyperparameter_sweep",
            "best_trial_number": best_trial_number,
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "train_accuracy": train_accuracy,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "hidden_dim": hidden_dim,
            "n_epochs": trainer.current_epoch + 1,
            "max_epochs": max_iter,
            "converged": trainer.current_epoch + 1 < max_iter,
        },
        infer_artifact=True,
    )

    # Also log as step metadata
    log_metadata(
        metadata={
            "hyperparameters": {
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "hidden_dim": hidden_dim,
            },
            "metrics": {
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
                "train_accuracy": train_accuracy,
            },
            "training": {
                "n_epochs": trainer.current_epoch + 1,
                "max_epochs": max_iter,
                "converged": trainer.current_epoch + 1 < max_iter,
            },
        }
    )

    return model
