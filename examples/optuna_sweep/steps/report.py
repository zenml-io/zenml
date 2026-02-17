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
"""Results reporting step using Optuna's tell API."""

from typing import Annotated, Any, Dict, List

import optuna
from optuna.trial import TrialState

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
def report_results(
    study_name: str,
    storage_url: str,
    results: List[Dict[str, Any]],
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Report trial results back to Optuna using the tell API.

    This step acts as a reducer, collecting results from all parallel
    training trials and reporting them back to the Optuna study. It
    prints a summary table and returns the best trial found.

    Args:
        study_name: Name of the Optuna study
        storage_url: Storage backend URL
        results: List of trial results from train_trial steps, each containing:
            - trial_number: Trial ID
            - val_loss: Validation loss
            - learning_rate, batch_size, hidden_dim: Hyperparameters
            - val_accuracy: Validation accuracy (optional)

    Returns:
        Summary dictionary containing:
        - best_trial_number: Trial with lowest validation loss
        - best_val_loss: Best validation loss achieved
        - best_params: Hyperparameters of best trial
        - n_trials: Total number of trials reported
        - all_trials: List of all trial summaries

    Example:
        >>> results = [
        ...     {"trial_number": 0, "val_loss": 0.45, "learning_rate": 0.001, ...},
        ...     {"trial_number": 1, "val_loss": 0.38, "learning_rate": 0.005, ...},
        ... ]
        >>> summary = report_results("my_study", "sqlite:///optuna.db", results)
        >>> print(summary["best_val_loss"])
        0.38
    """
    # Load study
    study = optuna.load_study(
        study_name=study_name,
        storage=storage_url,
    )

    print(
        f"\n📊 Reporting {len(results)} trial results to Optuna study '{study_name}'"
    )
    print("=" * 80)

    # Report each trial result using tell()
    for result in results:
        trial_number = result["trial_number"]
        val_loss = result["val_loss"]

        trial = next(
            (t for t in study.trials if t.number == trial_number), None
        )
        if trial is not None and trial.state != TrialState.RUNNING:
            print(
                f"Trial {trial_number:2d} | already reported (state={trial.state.name}), "
                f"skipping tell"
            )
            continue

        study.tell(trial_number, val_loss)

        print(
            f"Trial {trial_number:2d} | "
            f"val_loss={val_loss:.4f} | "
            f"learning_rate={result['learning_rate']:.6f} | "
            f"batch_size={result['batch_size']} | "
            f"hidden_dim={result['hidden_dim']} | "
            f"val_acc={result.get('val_accuracy', 0):.2f}%"
        )

    print("=" * 80)

    # Get best trial
    best_trial = study.best_trial
    print(f"\n🏆 Best Trial: {best_trial.number}")
    print(f"   Validation Loss: {best_trial.value:.4f}")
    print("   Hyperparameters:")
    for key, value in best_trial.params.items():
        print(f"      {key}: {value}")
    print()

    # Prepare summary
    summary = {
        "best_trial_number": best_trial.number,
        "best_val_loss": best_trial.value,
        "best_params": best_trial.params,
        "n_trials": len(results),
        "all_trials": [
            {
                "trial_number": r["trial_number"],
                "val_loss": r["val_loss"],
                "val_accuracy": r.get("val_accuracy", 0),
                "learning_rate": r["learning_rate"],
                "batch_size": r["batch_size"],
                "hidden_dim": r["hidden_dim"],
            }
            for r in results
        ],
    }

    # Show study statistics
    print("\n📈 Study Statistics:")
    print(f"   Total trials in study: {len(study.trials)}")
    print(f"   Trials reported this run: {len(results)}")
    print(f"   Best value overall: {study.best_value:.4f}")

    return summary
