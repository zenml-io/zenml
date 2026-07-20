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
"""Tier 0: the eval campaign + gate, on the active stack's Sandbox."""

from typing import Any, Dict, List, Optional

from steps.gate import gate_train_readiness

from zenml import pipeline
from zenml.integrations.harbor.steps import (
    build_harbor_matrix,
    build_harbor_report,
    run_harbor_shard,
)


@pipeline(dynamic=True)
def agentic_rl_eval(
    tasks: Optional[List[str]] = None,
    agents: Optional[List[Dict[str, Any]]] = None,
    trials_per_cell: int = 1,
    trials_per_step: int = 2,
    min_mean_reward: float = 0.05,
    max_mean_reward: float = 0.98,
) -> None:
    """Run a Harbor eval campaign and gate on the result.

    Caching stays ON (the pipeline default): every shard has a stable
    identity (committed task paths + agent config), so a rerun only
    re-executes failed or new shards and the gate is free the second
    time. This is the "cheap step protects the expensive step" shape —
    the trainer pipeline reuses these exact steps as its gate.

    Args:
        tasks: Task directories (defaults set by run.py: the committed
            taskset under ``tasks/``).
        agents: Harbor agent configs. The hermetic default is
            oracle-vs-nop, which needs no model API key.
        trials_per_cell: Trials per (task x agent) cell.
        trials_per_step: Trials packed into one mapped shard step.
        min_mean_reward: The gate's floor (broken-environment check).
        max_mean_reward: The gate's ceiling (saturation/headroom check).
    """
    shards = build_harbor_matrix(
        tasks=tasks,
        agents=agents,
        trials_per_cell=trials_per_cell,
        trials_per_step=trials_per_step,
    )
    results = run_harbor_shard.map(shard=shards)
    build_harbor_report(results=results)
    gate_train_readiness(
        results=results,
        min_mean_reward=min_mean_reward,
        max_mean_reward=max_mean_reward,
    )
