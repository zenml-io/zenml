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
"""Training step for individual Optuna trials."""

from typing import Annotated, Any, Dict

import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from zenml import log_metadata, step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=2,
            memory="4GB",
        )
    }
)
def train_trial(
    trial_config: Dict[str, Any],
    max_iter: int = 100,
) -> Annotated[Dict[str, Any], "trial_result"]:
    """Train a single trial with given hyperparameters.

    This step trains an MLPClassifier on FashionMNIST using the hyperparameters
    from the trial configuration. Training happens in isolation,
    allowing parallel execution across multiple trials.

    Args:
        trial_config: Trial configuration containing:
            - trial_number: Optuna trial ID
            - learning_rate_init: Initial learning rate
            - alpha: L2 regularization parameter
            - hidden_layer_sizes: Tuple defining hidden layer architecture
        max_iter: Maximum number of training iterations (default: 100)

    Returns:
        Dictionary containing trial results:
        - trial_number: Trial ID for reporting back to Optuna
        - val_loss: Validation loss (optimization metric)
        - learning_rate_init, alpha, hidden_layer_sizes: Hyperparameters used
        - training_losses: List of training losses per iteration

    Example:
        >>> config = {"trial_number": 0, "learning_rate_init": 0.001, "alpha": 0.0001, "hidden_layer_sizes": (128,)}
        >>> result = train_trial(config)
        >>> print(result["val_loss"])
        0.432
    """
    trial_number = trial_config["trial_number"]
    learning_rate_init = trial_config["learning_rate_init"]
    alpha = trial_config["alpha"]
    hidden_layer_sizes = trial_config["hidden_layer_sizes"]

    print(f"\n🚀 Training Trial {trial_number}")
    print(
        f"   learning_rate_init={learning_rate_init:.6f}, alpha={alpha:.6f}, hidden_layer_sizes={hidden_layer_sizes}"
    )

    # Load FashionMNIST dataset
    print("   Loading FashionMNIST dataset...")
    X, y = fetch_openml(
        "Fashion-MNIST", version=1, parser="auto", return_X_y=True
    )

    # Convert to numpy arrays and normalize to [0, 1] range
    X = np.array(X, dtype=np.float32) / 255.0
    y = np.array(y, dtype=np.int32)

    # Split into train and validation sets (80/20 split with fixed seed)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Standardize features for better MLP performance
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    print(f"   Train samples: {len(X_train)}, Val samples: {len(X_val)}")

    # Build and train MLPClassifier
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        learning_rate_init=learning_rate_init,
        alpha=alpha,
        max_iter=max_iter,
        random_state=42,
        verbose=False,
        early_stopping=False,  # We'll use validation_fraction for monitoring
        validation_fraction=0.1,  # 10% of training data for internal validation
        n_iter_no_change=10,  # Stop if no improvement for 10 iterations
    )

    # Train the model
    print(f"   Training MLPClassifier for up to {max_iter} iterations...")
    model.fit(X_train, y_train)

    # Get training loss history
    training_losses = (
        model.loss_curve_ if hasattr(model, "loss_curve_") else []
    )

    # Validation
    val_score = model.score(X_val, y_val)
    val_accuracy = val_score * 100

    # Calculate validation loss using log loss
    # MLPClassifier minimizes log loss, so we use 1 - accuracy as a proxy
    val_loss = 1.0 - val_score

    print(f"   Training iterations: {model.n_iter_}")
    print(f"   Validation: loss={val_loss:.4f}, accuracy={val_accuracy:.2f}%")
    print(f"✅ Trial {trial_number} complete\n")

    # Prepare result
    result = {
        "trial_number": trial_number,
        "val_loss": val_loss,
        "val_accuracy": val_accuracy,
        "learning_rate_init": learning_rate_init,
        "alpha": alpha,
        "hidden_layer_sizes": hidden_layer_sizes,
        "training_losses": [float(loss) for loss in training_losses],
        "n_iterations": model.n_iter_,
        "max_iter": max_iter,
    }

    # Log metadata for dashboard visibility and MCP server queries
    # This makes trials queryable: "show me all trials sorted by val_loss"
    # Explicitly attach to the trial_result output artifact
    log_metadata(
        metadata={
            "trial_number": trial_number,
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "learning_rate_init": learning_rate_init,
            "alpha": alpha,
            "hidden_layer_sizes": str(hidden_layer_sizes),
            "training_losses": [float(loss) for loss in training_losses],
            "final_train_loss": float(training_losses[-1])
            if training_losses
            else 0.0,
            "n_iterations": model.n_iter_,
        },
        artifact_name="trial_result",
        infer_artifact=True,  # Required when specifying artifact_name within a step
    )

    return result
