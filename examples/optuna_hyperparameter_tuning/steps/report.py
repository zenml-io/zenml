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
"""Results reporting step that aggregates trial results via ZenML artifacts.

This step does NOT depend on a shared Optuna storage backend. Instead it
accumulates results from all rounds through the previous_summary artifact,
making it portable across local and distributed orchestrators.
"""

from typing import Annotated, Any, Dict, List, Optional

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
    results: List[Dict[str, Any]],
    previous_summary: Optional[Dict[str, Any]] = None,
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Aggregate trial results and identify the best configuration.

    Combines results from the current round with any previous rounds
    (passed via previous_summary) and returns a cumulative summary.
    History flows through ZenML artifacts, so no shared database is needed.

    Args:
        results: List of trial results from the current round's train_trial
            steps, each containing:
            - trial_number: Trial ID
            - val_loss: Validation loss
            - learning_rate, batch_size, hidden_dim: Hyperparameters
            - val_accuracy: Validation accuracy percentage
        previous_summary: Optional summary from the previous round,
            containing all_trials from all prior rounds.

    Returns:
        Summary dictionary containing:
        - best_trial_number: Trial with lowest validation loss
        - best_val_loss: Best validation loss achieved
        - best_params: Hyperparameters of best trial
        - n_trials: Total number of trials across all rounds
        - all_trials: Cumulative list of all trial summaries

    Example:
        >>> results = [
        ...     {"trial_number": 0, "val_loss": 0.45, "learning_rate": 0.001, ...},
        ...     {"trial_number": 1, "val_loss": 0.38, "learning_rate": 0.005, ...},
        ... ]
        >>> summary = report_results(results)
        >>> print(summary["best_val_loss"])
        0.38
    """
    print(f"\n📊 Reporting {len(results)} trial results")
    print("=" * 80)

    all_trials: List[Dict[str, Any]] = []
    if previous_summary and previous_summary.get("all_trials"):
        all_trials.extend(previous_summary["all_trials"])
        print(
            f"   Carried forward {len(previous_summary['all_trials'])} "
            f"trials from previous rounds"
        )

    for result in results:
        trial_entry = {
            "trial_number": result["trial_number"],
            "val_loss": result["val_loss"],
            "val_accuracy": result.get("val_accuracy", 0),
            "learning_rate": result["learning_rate"],
            "batch_size": result["batch_size"],
            "hidden_dim": result["hidden_dim"],
        }
        all_trials.append(trial_entry)

        print(
            f"Trial {result['trial_number']:2d} | "
            f"val_loss={result['val_loss']:.4f} | "
            f"learning_rate={result['learning_rate']:.6f} | "
            f"batch_size={result['batch_size']} | "
            f"hidden_dim={str(result['hidden_dim']):>4s} | "
            f"val_acc={result.get('val_accuracy', 0):.2f}%"
        )

    print("=" * 80)

    best = min(all_trials, key=lambda t: t["val_loss"])

    print(f"\n🏆 Best Trial: {best['trial_number']}")
    print(f"   Validation Loss: {best['val_loss']:.4f}")
    print("   Hyperparameters:")
    print(f"      learning_rate: {best['learning_rate']}")
    print(f"      batch_size: {best['batch_size']}")
    print(f"      hidden_dim: {best['hidden_dim']}")

    summary = {
        "best_trial_number": best["trial_number"],
        "best_val_loss": best["val_loss"],
        "best_params": {
            "learning_rate": best["learning_rate"],
            "batch_size": best["batch_size"],
            "hidden_dim": best["hidden_dim"],
        },
        "n_trials": len(all_trials),
        "all_trials": all_trials,
    }

    print("\n📈 Study Statistics:")
    print(f"   Total trials across all rounds: {len(all_trials)}")
    print(f"   Trials reported this round: {len(results)}")
    print(f"   Best value overall: {best['val_loss']:.4f}")

    return summary
