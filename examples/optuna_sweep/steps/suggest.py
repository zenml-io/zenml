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
"""Trial suggestion step using Optuna's ask API."""

from typing import Annotated, Any, Dict, List, Optional

import optuna

from zenml import step
from zenml.config import ResourceSettings


@step(
    settings={
        "resources": ResourceSettings(
            cpu_count=1,
            memory="1GB",
        )
    }
)
def suggest_trials(
    study_name: str,
    storage_url: str,
    n_trials: int = 5,
    search_space: Optional[Dict[str, Any]] = None,
    previous_summary: Optional[Dict[str, Any]] = None,
) -> Annotated[List[Dict[str, Any]], "trial_configs"]:
    """Generate trial configurations using Optuna's ask API.

    This step creates or loads an Optuna study and uses the ask() method
    to generate hyperparameter configurations. Each configuration becomes
    a separate trial that will be trained in parallel.

    Args:
        study_name: Name of the Optuna study (persistent across runs)
        storage_url: Storage backend URL (e.g., "sqlite:///optuna.db")
        n_trials: Number of trial configurations to generate
        search_space: Optional search space configuration (defaults to
            standard ranges if not provided). Expected format:
            {
                "learning_rate": {"low": 1e-4, "high": 1e-2, "log": True},
                "batch_size": {"choices": [32, 64, 128, 256]},
                "hidden_dim": {"choices": [16, 32, 64, 128]}
            }
        previous_summary: Optional summary from previous round (used for DAG
            visualization to connect rounds). Not used in logic - Optuna's
            persistent storage already contains all previous trial results.

    Returns:
        List of trial configurations, each containing:
        - trial_number: Optuna trial number for reporting
        - learning_rate: Learning rate for optimizer
        - batch_size: Training batch size
        - hidden_dim: Number of filters in conv layers

    Example:
        >>> configs = suggest_trials("my_study", "sqlite:///optuna.db", n_trials=3)
        >>> print(configs[0])
        {'trial_number': 0, 'learning_rate': 0.001, 'batch_size': 64, 'hidden_dim': 32}
    """
    # Load or create study
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_url,
        load_if_exists=True,
        direction="minimize",  # Minimize validation loss
    )

    print(
        f"📊 Generating {n_trials} trial configurations for study '{study_name}'"
    )
    print(f"   Storage: {storage_url}")
    print(f"   Existing trials: {len(study.trials)}")

    # Use search space config if provided, otherwise use defaults
    # Lightweight defaults for CPU training
    if search_space is None:
        search_space = {
            "learning_rate": {"low": 1e-4, "high": 1e-2, "log": True},
            "batch_size": {"choices": [64, 128]},  # Smaller batches for CPU
            "hidden_dim": {"choices": [8, 16, 32]},  # Fewer filters
        }

    trial_configs = []

    for _ in range(n_trials):
        # Ask Optuna for a new trial suggestion
        trial = study.ask()

        # Suggest hyperparameters based on search space
        learning_rate_config = search_space["learning_rate"]
        learning_rate = trial.suggest_float(
            "learning_rate",
            learning_rate_config["low"],
            learning_rate_config["high"],
            log=learning_rate_config.get("log", False),
        )

        batch_size_config = search_space["batch_size"]
        batch_size = trial.suggest_categorical(
            "batch_size",
            batch_size_config["choices"],
        )

        hidden_dim_config = search_space["hidden_dim"]
        hidden_dim = trial.suggest_categorical(
            "hidden_dim",
            hidden_dim_config["choices"],
        )

        config = {
            "trial_number": trial.number,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "hidden_dim": hidden_dim,
        }
        trial_configs.append(config)

        print(
            f"   Trial {trial.number}: learning_rate={learning_rate:.6f}, "
            f"batch_size={batch_size}, hidden_dim={hidden_dim}"
        )

    print(f"✅ Generated {len(trial_configs)} trial configurations")

    return trial_configs
