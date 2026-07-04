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
"""Harbor eval campaign on the active stack's Sandbox, via the integration.

ZenML owns the outer orchestration (matrix expansion, per-shard steps,
retries, caching, aggregation); Harbor keeps the trial eval kernel (task
loading, agent loop, verifier, reward). All reusable machinery lives in
``zenml.integrations.harbor`` — this example only composes the steps.

Invocation::

    python run.py [task] [agent_name] [n_trials]   # default: tasks/hello, oracle, 3

``task`` is a local task directory (``tasks/hello``) or a Harbor registry
dataset (``dataset:terminal-bench-sample@2.0``), which expands into one
trial per benchmark task::

    python run.py dataset:terminal-bench@2.0 oracle 1   # the full 89-task benchmark
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from zenml import pipeline
from zenml.integrations.harbor.steps import (
    build_harbor_matrix,
    build_harbor_report,
    run_harbor_shard,
)

_DEFAULT_TASK = "tasks/hello"
_DEFAULT_AGENT = "oracle"
_DATASET_PREFIX = "dataset:"


@pipeline(dynamic=True)
def sandbox_harbor_pipeline(
    tasks: Optional[List[str]] = None,
    dataset: Optional[Dict[str, Any]] = None,
    agent_name: str = _DEFAULT_AGENT,
    n_trials: int = 3,
    trials_per_step: int = 1,
) -> None:
    """Matrix fan-out: one campaign shard per mapped ZenML step.

    Step caching is left enabled, so rerunning an identical campaign
    only executes shards that don't have a completed run yet — failed
    shards rerun, finished ones are cache hits.
    """
    shards = build_harbor_matrix(
        tasks=tasks,
        dataset=dataset,
        agents=[{"name": agent_name}],
        trials_per_cell=n_trials,
        trials_per_step=trials_per_step,
    )
    results = run_harbor_shard.map(shard=shards)
    build_harbor_report(results=results)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TASK
    agent = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_AGENT
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    tasks: Optional[List[str]] = None
    dataset: Optional[Dict[str, Any]] = None
    if task.startswith(_DATASET_PREFIX):
        name, _, version = task[len(_DATASET_PREFIX) :].partition("@")
        dataset = {"name": name, "version": version or None}
    elif task.startswith("git+"):
        tasks = [task]
    else:
        # Resolve local tasks relative to this file so the example works
        # from any working directory.
        path = Path(task)
        if not path.is_absolute():
            path = (Path(__file__).parent / path).resolve()
        tasks = [str(path)]

    print(
        "Running ZenML pipeline (Harbor campaign on the active stack's sandbox) ..."
    )
    print(f"  task   = {task}")
    print(f"  agent  = {agent}")
    print(f"  trials = {trials}")
    sandbox_harbor_pipeline(
        tasks=tasks, dataset=dataset, agent_name=agent, n_trials=trials
    )
    print("Done. Check the ZenML dashboard for the run + report.")
