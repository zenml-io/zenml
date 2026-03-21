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

from typing import Annotated, Any, Dict

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
def retrain_best_model(
    sweep_summary: Dict[str, Any],
    max_iter: int = 20,
) -> Annotated[LightningModule, "best_model"]:
    """Retrain the best model from hyperparameter sweep for production.

    This step identifies the best trial from the sweep results, then
    retrains a model with those hyperparameters using more epochs
    for better convergence. The final model is saved as a ZenML artifact.

    Args:
        sweep_summary: Summary from report_results containing best_params
        max_iter: Maximum training epochs for final model (default: 20,
            typically overridden by pipeline to a higher value for better convergence)

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

    learning_rate = best_params["learning_rate"]
    batch_size = best_params["batch_size"]
    hidden_dim = best_params["hidden_dim"]

    print("   Loading FashionMNIST dataset...")
    train_loader, val_loader = get_fashion_mnist_loaders(batch_size=batch_size)
    print(
        f"   Train samples: {len(train_loader.dataset)}, Val samples: {len(val_loader.dataset)}"
    )

    model = FashionMNISTClassifier(
        learning_rate=learning_rate,
        hidden_dim=hidden_dim,
    )

    trainer = Trainer(
        max_epochs=max_iter,
        accelerator="auto",
        devices=1,
        callbacks=[
            EarlyStopping(
                monitor="val_loss",
                patience=15,  # More patience for production
                mode="min",
            ),
        ],
        enable_checkpointing=False,
        enable_progress_bar=False,
        logger=False,
        deterministic=True,
    )

    print(f"   Training production model (up to {max_iter} epochs)...")
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
    print("✅ Production model trained and ready\n")

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
