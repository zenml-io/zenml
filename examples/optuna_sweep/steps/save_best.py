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

from typing import Annotated, Any, Dict, List

import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from zenml import log_metadata, log_model_metadata, step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            memory="4GB",
        )
    }
)
def retrain_best_model(
    sweep_summary: Dict[str, Any],
    max_iter: int = 200,
) -> Annotated[MLPClassifier, "best_model"]:
    """Retrain the best model from hyperparameter sweep for production.

    This step identifies the best trial from the sweep results, then
    retrains a model with those hyperparameters using more iterations
    for better convergence. The final model is saved as a ZenML artifact.

    Args:
        sweep_summary: Summary from report_results containing best_params
        max_iter: Maximum training iterations for final model (default: 200,
            higher than sweep trials for better convergence)

    Returns:
        Trained MLPClassifier model with best hyperparameters, ready for
        production use

    Example:
        >>> summary = {"best_params": {"learning_rate_init": 0.001, ...}}
        >>> model = retrain_best_model(summary, max_iter=200)
        >>> # Model is automatically saved as ZenML artifact
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
    print(f"   Training for {max_iter} iterations (more than sweep trials)")

    # Extract hyperparameters
    learning_rate_init = best_params["learning_rate_init"]
    alpha = best_params["alpha"]

    # Convert hidden_layer_sizes string back to tuple if needed
    hidden_layer_sizes = best_params["hidden_layer_sizes"]
    if isinstance(hidden_layer_sizes, str):
        hidden_layer_sizes = tuple(map(int, hidden_layer_sizes.split(",")))
    elif isinstance(hidden_layer_sizes, list):
        hidden_layer_sizes = tuple(hidden_layer_sizes)

    # Load FashionMNIST dataset (same as training trials)
    print("   Loading FashionMNIST dataset...")
    X, y = fetch_openml(
        "Fashion-MNIST", version=1, parser="auto", return_X_y=True
    )

    # Convert to numpy arrays and normalize
    X = np.array(X, dtype=np.float32) / 255.0
    y = np.array(y, dtype=np.int32)

    # Split into train and validation sets (same split as trials)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Standardize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    print(f"   Train samples: {len(X_train)}, Val samples: {len(X_val)}")

    # Build model with best hyperparameters
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        learning_rate_init=learning_rate_init,
        alpha=alpha,
        max_iter=max_iter,  # More iterations for production model
        random_state=42,
        verbose=False,
        early_stopping=True,  # Enable early stopping for production
        validation_fraction=0.1,
        n_iter_no_change=15,  # More patience for production
    )

    # Train the production model
    print(f"   Training production model (up to {max_iter} iterations)...")
    model.fit(X_train, y_train)

    # Evaluate on validation set
    val_score = model.score(X_val, y_val)
    val_accuracy = val_score * 100
    val_loss = 1.0 - val_score

    # Also evaluate on training set for completeness
    train_score = model.score(X_train, y_train)
    train_accuracy = train_score * 100

    print(f"   Training iterations: {model.n_iter_}")
    print(
        f"   Final validation: loss={val_loss:.4f}, accuracy={val_accuracy:.2f}%"
    )
    print(f"   Final training: accuracy={train_accuracy:.2f}%")
    print("✅ Production model trained and ready\n")

    # Log metadata on the model artifact
    # This makes the model queryable in the dashboard
    log_metadata(
        metadata={
            "source": "hyperparameter_sweep",
            "best_trial_number": best_trial_number,
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "train_accuracy": train_accuracy,
            "learning_rate_init": learning_rate_init,
            "alpha": alpha,
            "hidden_layer_sizes": str(hidden_layer_sizes),
            "n_iterations": model.n_iter_,
            "max_iter": max_iter,
            "converged": model.n_iter_ < max_iter,
        },
        infer_artifact=True,
    )

    # Also log as metadata
    log_metadata(
        metadata={
            "hyperparameters": {
                "learning_rate_init": learning_rate_init,
                "alpha": alpha,
                "hidden_layer_sizes": str(hidden_layer_sizes),
            },
            "metrics": {
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
                "train_accuracy": train_accuracy,
            },
            "training": {
                "n_iterations": model.n_iter_,
                "max_iter": max_iter,
                "converged": model.n_iter_ < max_iter,
            },
        }
    )

    return model
