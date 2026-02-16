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
"""Hyperparameter sweep pipelines using Optuna + ZenML dynamic pipelines."""

from typing import Annotated, Any, Dict, Optional

from steps import (
    report_results,
    retrain_best_model,
    suggest_trials,
    train_trial,
)

from zenml import pipeline


@pipeline(dynamic=True)
def sweep_pipeline(
    study_name: str = "fashion_mnist_sweep",
    storage_url: str = "sqlite:///optuna_study.db",
    n_trials: int = 5,
    max_iter: int = 100,
    search_space: Optional[Dict[str, Any]] = None,
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Simple parallel hyperparameter sweep using Optuna + ZenML.

    This pipeline demonstrates the basic pattern for hyperparameter optimization:
    1. Generate N trial configurations using Optuna's ask() API
    2. Fan out to train N models in parallel using .map()
    3. Report all results back to Optuna using tell() API

    All N trials run in parallel. Perfect for small-scale sweeps where you
    want maximum parallelism.

    Args:
        study_name: Name of the Optuna study (persistent across runs)
        storage_url: Optuna storage backend URL (e.g., "sqlite:///optuna.db")
        n_trials: Number of trials to run in parallel
        max_iter: Maximum training iterations per trial (default: 100)
        search_space: Optional custom search space configuration
        enable_cache: Whether to enable caching (default: True)

    Returns:
        Summary dictionary with best trial info and all results

    Example:
        >>> # Run with default cache enabled
        >>> summary = sweep_pipeline(
        ...     study_name="my_sweep",
        ...     storage_url="sqlite:///optuna.db",
        ...     n_trials=10,
        ... )
        >>> print(f"Best val_loss: {summary['best_val_loss']:.4f}")
        >>>
        >>> # Disable cache via with_options
        >>> summary = sweep_pipeline.with_options(enable_cache=False)(
        ...     study_name="my_sweep",
        ...     storage_url="sqlite:///optuna.db",
        ...     n_trials=10,
        ... )

    Pipeline DAG:
        suggest_trials
             │
             ├── train_trial_0 ──┐
             ├── train_trial_1   │
             ├── train_trial_2   ├── (parallel fan-out via .map())
             ├── train_trial_3   │
             └── train_trial_4 ──┘
                     │
                report_results
    """
    # Generate trial configurations
    trials = suggest_trials(
        study_name=study_name,
        storage_url=storage_url,
        n_trials=n_trials,
        search_space=search_space,
    )

    # Fan out: train all trials in parallel
    # .map() creates one step per trial, executing in parallel
    results = train_trial.with_options(parameters={"max_iter": max_iter}).map(
        trial_config=trials
    )

    # Reduce: report all results back to Optuna
    summary = report_results(
        study_name=study_name,
        storage_url=storage_url,
        results=results,
    )

    # Retrain best model with more iterations for production
    # Model is saved as ZenML artifact automatically, no need to return it
    _ = retrain_best_model(
        sweep_summary=summary,
        max_iter=200,  # More iterations than trials for better convergence
    )

    return summary


@pipeline(dynamic=True)
def adaptive_sweep_pipeline(
    study_name: str = "fashion_mnist_sweep",
    storage_url: str = "sqlite:///optuna_study.db",
    n_rounds: int = 3,
    trials_per_round: int = 3,
    max_iter: int = 100,
    search_space: Optional[Dict[str, Any]] = None,
) -> Annotated[Dict[str, Any], "sweep_summary"]:
    """Adaptive hyperparameter sweep with multiple rounds of optimization.

    This pipeline runs the sweep in batches (rounds), allowing Optuna to
    learn from completed trials before suggesting new ones. This is more
    sample-efficient for large search spaces.

    Each round:
    1. Suggests new trials based on previous results
    2. Trains trials in parallel
    3. Reports results, which inform the next round's suggestions

    Use this when you want Optuna's adaptive sampling to learn from
    early trials before launching later ones.

    Args:
        study_name: Name of the Optuna study
        storage_url: Optuna storage backend URL
        n_rounds: Number of optimization rounds
        trials_per_round: Parallel trials per round
        max_iter: Maximum training iterations per trial
        search_space: Optional custom search space configuration

    Returns:
        Summary dictionary from the final round

    Example:
        >>> # Run with default cache enabled
        >>> summary = adaptive_sweep_pipeline(
        ...     study_name="adaptive_sweep",
        ...     n_rounds=5,
        ...     trials_per_round=4,
        ... )
        >>>
        >>> # Disable cache via with_options
        >>> summary = adaptive_sweep_pipeline.with_options(enable_cache=False)(
        ...     study_name="adaptive_sweep",
        ...     n_rounds=5,
        ...     trials_per_round=4,
        ... )

    Pipeline DAG (3 rounds, 3 trials/round):
        Round 1:
            suggest_trials_round_0
                 │
                 ├── train_trial_0 ──┐
                 ├── train_trial_1   ├── (parallel)
                 └── train_trial_2 ──┘
                         │
                    report_results_round_0

        Round 2:
            suggest_trials_round_1 (learns from round 1)
                 │
                 ├── train_trial_3 ──┐
                 ├── train_trial_4   ├── (parallel)
                 └── train_trial_5 ──┘
                         │
                    report_results_round_1

        Round 3:
            suggest_trials_round_2 (learns from rounds 1 & 2)
                 │
                 ├── train_trial_6 ──┐
                 ├── train_trial_7   ├── (parallel)
                 └── train_trial_8 ──┘
                         │
                    report_results_round_2
    """
    # Initialize with minimal dict to avoid None artifact on first round
    summary = {"round": 0, "is_initial": True}

    for round_idx in range(n_rounds):
        print(f"\n{'=' * 80}")
        print(f"🔄 Round {round_idx + 1}/{n_rounds}")
        print(f"{'=' * 80}\n")

        # Generate trials for this round
        # Pass previous_summary to create DAG edge between rounds
        # (first round gets minimal dict, subsequent rounds get real summary)
        trials = suggest_trials(
            study_name=study_name,
            storage_url=storage_url,
            n_trials=trials_per_round,
            search_space=search_space,
            previous_summary=summary,  # Creates visual connection in DAG
        )

        # Train trials in parallel
        results = train_trial.with_options(
            parameters={"max_iter": max_iter}
        ).map(trial_config=trials)

        # Report results (informs next round's suggestions)
        summary = report_results(
            study_name=study_name,
            storage_url=storage_url,
            results=results,
        )

    # Retrain best model with more iterations for production
    # Model is saved as ZenML artifact automatically, no need to return it
    _ = retrain_best_model(
        sweep_summary=summary,
        max_iter=200,  # More iterations than trials
    )

    # Return summary from final round
    return summary  # type: ignore[return-value]
