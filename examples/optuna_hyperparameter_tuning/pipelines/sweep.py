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
"""Hyperparameter sweep pipelines using Optuna + ZenML dynamic pipelines.

Trial history flows through ZenML artifacts (not a shared Optuna database),
so these pipelines work on any orchestrator -- local or distributed.
"""

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
    n_trials: int = 5,
    max_iter: int = 10,
) -> None:
    """Simple parallel hyperparameter sweep using Optuna + ZenML.

    This pipeline demonstrates the basic pattern for hyperparameter optimization:
    1. Generate N trial configurations using Optuna's ask() API
    2. Fan out to train N models in parallel using .map()
    3. Aggregate all results and identify the best configuration

    All N trials run in parallel. Perfect for small-scale sweeps where you
    want maximum parallelism.

    Args:
        study_name: Name of the Optuna study (for logging)
        n_trials: Number of trials to run in parallel
        max_iter: Maximum training epochs per trial (default: 10)

    Pipeline DAG:
        suggest_trials
             |
             +-- train_trial_0 --+
             +-- train_trial_1   |
             +-- train_trial_2   +-- (parallel fan-out via .map())
             +-- train_trial_3   |
             +-- train_trial_4 --+
                     |
                report_results
    """
    trials = suggest_trials(
        study_name=study_name,
        n_trials=n_trials,
    )

    results = train_trial.with_options(parameters={"max_iter": max_iter}).map(
        trial_config=trials
    )

    summary = report_results(results=results)

    _ = retrain_best_model(
        sweep_summary=summary,
        max_iter=200,
    )


@pipeline(dynamic=True)
def adaptive_sweep_pipeline(
    study_name: str = "fashion_mnist_sweep",
    n_rounds: int = 3,
    trials_per_round: int = 3,
    max_iter: int = 10,
) -> None:
    """Adaptive hyperparameter sweep with multiple rounds of optimization.

    This pipeline runs the sweep in batches (rounds), allowing Optuna to
    learn from completed trials before suggesting new ones. This is more
    sample-efficient for large search spaces.

    Each round:
    1. Suggests new trials based on previous results (via artifact history)
    2. Trains trials in parallel
    3. Reports results, which inform the next round's suggestions

    Trial history flows through ZenML artifacts, so this works on any
    orchestrator -- local or distributed.

    Args:
        study_name: Name of the Optuna study (for logging)
        n_rounds: Number of optimization rounds
        trials_per_round: Parallel trials per round
        max_iter: Maximum training iterations per trial

    Example:
        >>> adaptive_sweep_pipeline(
        ...     study_name="adaptive_sweep",
        ...     n_rounds=5,
        ...     trials_per_round=4,
        ... )

    Pipeline DAG (3 rounds, 3 trials/round):
        Round 1:
            suggest_trials_round_0
                 |
                 +-- train_trial_0 --+
                 +-- train_trial_1   +-- (parallel)
                 +-- train_trial_2 --+
                         |
                    report_results_round_0

        Round 2:
            suggest_trials_round_1 (learns from round 1)
                 |
                 +-- train_trial_3 --+
                 +-- train_trial_4   +-- (parallel)
                 +-- train_trial_5 --+
                         |
                    report_results_round_1

        Round 3:
            suggest_trials_round_2 (learns from rounds 1 & 2)
                 |
                 +-- train_trial_6 --+
                 +-- train_trial_7   +-- (parallel)
                 +-- train_trial_8 --+
                         |
                    report_results_round_2
    """
    summary = {"round": 0, "is_initial": True}

    for round_idx in range(n_rounds):
        print(f"\n{'=' * 80}")
        print(f"🔄 Round {round_idx + 1}/{n_rounds}")
        print(f"{'=' * 80}\n")

        trials = suggest_trials(
            study_name=study_name,
            n_trials=trials_per_round,
            previous_summary=summary,
        )

        results = train_trial.with_options(
            parameters={"max_iter": max_iter}
        ).map(trial_config=trials)

        summary = report_results(
            results=results,
            previous_summary=summary,
        )

    _ = retrain_best_model(
        sweep_summary=summary,
        max_iter=200,
    )
