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
"""Trial suggestion step using Optuna's ask API with in-memory studies.

The Optuna study is created in-memory at each invocation and seeded with
results from previous rounds (passed via ZenML artifacts). This avoids
the need for a shared persistent Optuna storage backend, making the
pipeline portable across local and distributed orchestrators.
"""

from typing import Annotated, Any, Dict, List, Optional

import optuna
from optuna.distributions import CategoricalDistribution, FloatDistribution

from zenml import step
from zenml.config import ResourceSettings

SEARCH_SPACE: Dict[str, Any] = {
    "learning_rate": {"low": 1e-4, "high": 1e-2, "log": True},
    "batch_size": {"choices": [64, 128]},
    "hidden_dim": {"choices": [8, 16, 32]},
}


def _build_distributions(
    search_space: Dict[str, Any],
) -> Dict[str, Any]:
    """Build Optuna distribution objects from a search space config dict."""
    distributions: Dict[str, Any] = {}

    lr_cfg = search_space["learning_rate"]
    distributions["learning_rate"] = FloatDistribution(
        low=lr_cfg["low"],
        high=lr_cfg["high"],
        log=lr_cfg.get("log", False),
    )

    bs_cfg = search_space["batch_size"]
    distributions["batch_size"] = CategoricalDistribution(
        choices=bs_cfg["choices"],
    )

    hd_cfg = search_space["hidden_dim"]
    distributions["hidden_dim"] = CategoricalDistribution(
        choices=hd_cfg["choices"],
    )

    return distributions


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
    n_trials: int = 5,
    previous_summary: Optional[Dict[str, Any]] = None,
) -> Annotated[List[Dict[str, Any]], "trial_configs"]:
    """Generate trial configurations using Optuna's ask API.

    Creates an in-memory Optuna study, replays any previous trial results
    into it (so the TPE sampler learns from history), then uses ask() to
    generate new hyperparameter suggestions.

    History flows through ZenML artifacts (previous_summary) rather than
    a shared database, so this works on any orchestrator.

    Args:
        study_name: Name of the Optuna study (for logging)
        n_trials: Number of trial configurations to generate
        previous_summary: Optional summary from a previous round containing
            all_trials with results. Used to seed the Optuna sampler so it
            makes informed suggestions based on prior observations.

    Returns:
        List of trial configurations, each containing:
        - trial_number: Optuna trial number for identification
        - learning_rate: Learning rate for optimizer
        - batch_size: Training batch size
        - hidden_dim: Number of filters in conv layers

    Example:
        >>> configs = suggest_trials("my_study", n_trials=3)
        >>> print(configs[0])
        {'trial_number': 0, 'learning_rate': 0.001, 'batch_size': 64, 'hidden_dim': 32}
    """
    study = optuna.create_study(
        study_name=study_name,
        direction="minimize",
    )

    # Replay previous trial results so the TPE sampler learns from them
    if previous_summary and previous_summary.get("all_trials"):
        distributions = _build_distributions(SEARCH_SPACE)
        for trial_info in previous_summary["all_trials"]:
            study.add_trial(
                optuna.trial.create_trial(
                    params={
                        "learning_rate": trial_info["learning_rate"],
                        "batch_size": trial_info["batch_size"],
                        "hidden_dim": trial_info["hidden_dim"],
                    },
                    distributions=distributions,
                    values=[trial_info["val_loss"]],
                    state=optuna.trial.TrialState.COMPLETE,
                )
            )

    n_previous = len(study.trials)
    print(
        f"📊 Generating {n_trials} trial configurations for study '{study_name}'"
    )
    print(f"   Previous trials replayed: {n_previous}")

    trial_configs = []

    for _ in range(n_trials):
        trial = study.ask()

        lr_cfg = SEARCH_SPACE["learning_rate"]
        learning_rate = trial.suggest_float(
            "learning_rate",
            lr_cfg["low"],
            lr_cfg["high"],
            log=lr_cfg.get("log", False),
        )

        bs_cfg = SEARCH_SPACE["batch_size"]
        batch_size = trial.suggest_categorical(
            "batch_size",
            bs_cfg["choices"],
        )

        hd_cfg = SEARCH_SPACE["hidden_dim"]
        hidden_dim = trial.suggest_categorical(
            "hidden_dim",
            hd_cfg["choices"],
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
