#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""The gate between the cheap eval campaign and the expensive trainer."""

from typing import Any, Dict, List

from zenml import log_metadata, step
from zenml.integrations.harbor.models import HarborShardResult
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def gate_train_readiness(
    results: List[HarborShardResult],
    min_mean_reward: float = 0.05,
    max_mean_reward: float = 0.98,
    allow_errored_trials: bool = False,
) -> Dict[str, Any]:
    """Decide whether the eval campaign clears the trainer for launch.

    Ordering is deliberate and load-bearing: **errors are checked before
    rewards.** Errored shards log no ``harbor.mean_reward`` at all, and
    the ``0.0`` sentinel only fires when *all* trials of a shard
    errored, so a reward-threshold gate on its own reads a broken
    campaign as a passing one. A scorer that crashed is not a scorer
    that returned 0.0, and a reward-only gate cannot tell them apart.

    The upper bound is the headroom check: if the gate model already
    saturates the task set, training has nothing to learn into.

    Args:
        results: The gate campaign's shard results.
        min_mean_reward: Floor for the campaign mean reward; below it
            the environment is considered broken or too hard.
        max_mean_reward: Ceiling for the campaign mean reward; above it
            the task set is saturated and training is pointless.
        allow_errored_trials: Whether errored trials merely warn
            instead of failing the gate.

    Returns:
        The gate verdict with the campaign statistics it was based on.

    Raises:
        RuntimeError: If any trial errored (unless allowed), if no trial
            produced a reward, or if the campaign mean is outside the
            [min, max] window. Raising here is the protection: in a
            dynamic pipeline the trainer step after this call never
            launches, so the GPU is never billed for a doomed run.
    """
    n_trials = sum(result.n_total_trials for result in results)
    n_errored = sum(result.n_errored for result in results)
    rewards = [
        reward
        for result in results
        for trial in result.trials
        for reward in (trial.rewards or {}).values()
        if reward is not None
    ]

    verdict: Dict[str, Any] = {
        "n_shards": len(results),
        "n_trials": n_trials,
        "n_errored": n_errored,
        "n_rewards": len(rewards),
        "mean_reward": sum(rewards) / len(rewards) if rewards else None,
        "passed": False,
    }
    log_metadata(
        metadata={f"gate.{key}": value for key, value in verdict.items()}
    )

    if n_errored and not allow_errored_trials:
        raise RuntimeError(
            f"Gate failed: {n_errored}/{n_trials} trials ERRORED. A "
            "crashed trial is not a low reward — fix the environment "
            "(image, task, sandbox) before spending GPU time. Shard "
            "logs carry the root cause (download_jobs_dir)."
        )
    if n_errored:
        logger.warning(
            "Gate tolerating %d errored trials (allow_errored_trials).",
            n_errored,
        )

    if not rewards:
        raise RuntimeError(
            "Gate failed: no trial produced a reward. The campaign "
            "ran but nothing was scored — this is an environment "
            "problem, not a model problem."
        )

    mean_reward = verdict["mean_reward"]
    assert mean_reward is not None
    if mean_reward < min_mean_reward:
        raise RuntimeError(
            f"Gate failed: mean reward {mean_reward:.3f} < "
            f"{min_mean_reward}. The environment is likely broken or "
            "the task set is too hard for the policy to get any "
            "learning signal."
        )
    if mean_reward > max_mean_reward:
        raise RuntimeError(
            f"Gate failed: mean reward {mean_reward:.3f} > "
            f"{max_mean_reward}. The task set is saturated — there is "
            "no headroom for training to improve into."
        )

    verdict["passed"] = True
    log_metadata(metadata={"gate.passed": True})
    logger.info(
        "Gate passed: mean reward %.3f over %d rewards, 0 blocking errors.",
        mean_reward,
        len(rewards),
    )
    return verdict
