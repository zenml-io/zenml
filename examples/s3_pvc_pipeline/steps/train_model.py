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
"""Training step using PyTorch Lightning."""

from pathlib import Path
from typing import Annotated, Any, Dict

import torch
from lightning import Trainer
from lightning.pytorch.callbacks import EarlyStopping

from steps.dataloader import get_dataloader
from steps.model import FashionMNISTClassifier
from zenml import log_metadata, step


@step
def train_model(
    preprocessed_paths: Dict[str, str],
    hyperparams: Dict[str, Any],
    seed: int,
) -> Annotated[str, "trained_model_path"]:
    """Train a model with the given hyperparameters.

    Saves the model under the same versioned base as the data (e.g. /mnt/data/v1/models/model/).
    Train result is printed and logged as metadata only (not returned).

    Args:
        preprocessed_paths: Dict with "train", "val", "test" keys pointing to data directory paths on PVC.
        hyperparams: Training hyperparameters (learning_rate, batch_size, hidden_dim, max_epochs).
        seed: Random seed for reproducibility.

    Returns:
        Path to the saved model file on PVC.
    """
    learning_rate = hyperparams["learning_rate"]
    batch_size = hyperparams["batch_size"]
    hidden_dim = hyperparams["hidden_dim"]
    max_epochs = hyperparams.get("max_epochs", 1)

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    print("\nTraining model")
    print(
        f"learning_rate={learning_rate:.6f}, batch_size={batch_size},"
        f" hidden_dim={hidden_dim}, max_epochs={max_epochs}"
    )

    print("Loading data from PVC")
    train_loader = get_dataloader(
        preprocessed_paths["train"], batch_size=batch_size, shuffle=True
    )
    val_loader = get_dataloader(
        preprocessed_paths["val"], batch_size=256, shuffle=False
    )
    n_train = len(train_loader.dataset)  # type: ignore[arg-type]
    n_val = len(val_loader.dataset)  # type: ignore[arg-type]
    print(f"   Train samples: {n_train}, Val samples: {n_val}")

    model = FashionMNISTClassifier(
        learning_rate=learning_rate, hidden_dim=hidden_dim
    )
    trainer = Trainer(
        max_epochs=max_epochs,
        accelerator="auto",
        devices=1,
        callbacks=[EarlyStopping(monitor="val_loss", patience=10, mode="min")],
        enable_progress_bar=False,
        logger=False,
        deterministic=True,
    )

    print(f"   Training for up to {max_epochs} epochs...")
    trainer.fit(model, train_loader, val_loader)

    val_loss = float(trainer.callback_metrics.get("val_loss", 0.0))
    val_accuracy = float(trainer.callback_metrics.get("val_acc", 0.0)) * 100
    result = {
        "val_loss": val_loss,
        "val_accuracy": val_accuracy,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "hidden_dim": hidden_dim,
        "n_epochs": trainer.current_epoch + 1,
        "max_epochs": max_epochs,
    }

    print("\n  Train result")
    print("  ------------")
    print(f"    val_loss:     {val_loss:.4f}")
    print(f"    val_accuracy: {val_accuracy:.2f}%")
    print(f"    epochs:       {result['n_epochs']} / {max_epochs}")
    print("  Training complete\n")

    log_metadata(
        metadata={
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "hidden_dim": hidden_dim,
            "n_epochs": result["n_epochs"],
        },
    )

    # Save model under same versioned base as data (e.g. /mnt/data/v1/models/model).
    base_dir = Path(preprocessed_paths["train"]).parent
    model_dir = base_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.pt"
    torch.save(model, model_path)
    print(f"   Model saved to {model_path}")

    return str(model_path)
