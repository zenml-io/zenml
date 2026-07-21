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
"""Harbor agent-eval campaign on the active stack's Sandbox.

ZenML owns the outer orchestration (matrix expansion, per-shard steps,
retries, caching, aggregation); Harbor keeps the trial eval kernel (task
loading, agent loop, verifier, reward). All reusable machinery lives in
``zenml.integrations.harbor`` — this example only composes the steps.

The default campaign is a hermetic head-to-head that needs no LLM keys:
the ``oracle`` agent (runs the task's reference solution, reward 1.0)
against the ``nop`` agent (does nothing, reward 0.0) on ``tasks/hello``,
3 trials each, packed 2 trials per shard. Rerun the same command and
watch completed shards cache-hit — only failed or new shards execute.

Invocation::

    python run.py [task] [agent] [n_trials]   # default: tasks/hello, oracle vs nop, 3

``task`` is a local task directory, a pinned ``git+URL@COMMIT:SUBPATH``
ref, or a Harbor registry dataset (``dataset:terminal-bench-sample@2.0``),
which expands into one campaign cell per benchmark task. Passing an
explicit ``agent`` runs just that agent instead of the head-to-head.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from zenml import pipeline
from zenml.client import Client
from zenml.integrations.harbor.steps import (
    build_harbor_matrix,
    build_harbor_report,
    run_harbor_shard,
)

_DEFAULT_TASK = "tasks/hello"
# oracle solves every task via its reference solution; nop attempts
# nothing — a hermetic reward contrast for the campaign report.
_DEFAULT_AGENTS = [{"name": "oracle"}, {"name": "nop"}]
_DATASET_PREFIX = "dataset:"


@pipeline(dynamic=True)
def harbor_agent_evals(
    tasks: Optional[List[str]] = None,
    dataset: Optional[Dict[str, Any]] = None,
    agents: Optional[List[Dict[str, Any]]] = None,
    trials_per_cell: int = 3,
    trials_per_step: int = 2,
) -> None:
    """Matrix fan-out: one campaign shard per mapped ZenML step."""
    shards = build_harbor_matrix(
        tasks=tasks,
        dataset=dataset,
        agents=agents,
        trials_per_cell=trials_per_cell,
        trials_per_step=trials_per_step,
    )
    results = run_harbor_shard.map(shard=shards)
    build_harbor_report(results=results)


def show_results() -> None:
    """Print the campaign receipts: report, metadata query, log restore."""
    client = Client()
    run = client.list_pipeline_runs(
        pipeline="harbor_agent_evals", sort_by="desc:created", size=1
    ).items[0]

    report = run.steps["build_harbor_report"].outputs["harbor_report"][0]
    print("\n" + report.load() + "\n")

    # Shard steps log harbor.* metadata — the queryable surface. On
    # current servers this also filters server-side, e.g.
    # client.list_run_steps(run_metadata=["harbor.mean_reward:lt:1"]).
    shard_steps = [
        step
        for name, step in run.steps.items()
        if name.startswith("map:run_harbor_shard:")
    ]
    losing = [
        step
        for step in shard_steps
        if float(step.run_metadata.get("harbor.mean_reward", 1)) < 1
    ]
    print(f"Shards with mean reward < 1 (via step metadata): {len(losing)}")
    for step in losing:
        print(
            f"  {step.name}: agent={step.run_metadata.get('harbor.agent')} "
            f"mean_reward={step.run_metadata.get('harbor.mean_reward')}"
        )

    # Every shard artifact carries Harbor's full job tree (agent and
    # verifier logs, trajectory) — restore one on demand.
    if losing:
        shard_result = losing[0].outputs["harbor_shard_result"][0].load()
        target = Path("harbor_logs") / shard_result.job_name
        shard_result.download_jobs_dir(target)
        print(f"Restored Harbor logs of {losing[0].name} to {target}/")


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TASK
    agents = [{"name": sys.argv[2]}] if len(sys.argv) > 2 else _DEFAULT_AGENTS
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    tasks: Optional[List[str]] = None
    dataset: Optional[Dict[str, Any]] = None
    if task.startswith(_DATASET_PREFIX):
        name, _, version = task[len(_DATASET_PREFIX) :].partition("@")
        # An optional trailing :N slices the dataset to its first N
        # tasks (e.g. dataset:terminal-bench-sample@2.0:3) so a first
        # benchmark run doesn't fan out the full task set.
        n_tasks: Optional[int] = None
        version, _, slice_part = version.partition(":")
        if slice_part:
            n_tasks = int(slice_part)
        dataset = {
            "name": name,
            "version": version or None,
            "n_tasks": n_tasks,
        }
    elif task.startswith("git+"):
        tasks = [task]
    else:
        # Resolve local tasks relative to this file so the example works
        # from any working directory.
        path = Path(task)
        if not path.is_absolute():
            path = (Path(__file__).parent / path).resolve()
        tasks = [str(path)]

    print("Running Harbor agent evals on the active stack's sandbox ...")
    print(f"  task    = {task}")
    print(f"  agents  = {', '.join(a['name'] for a in agents)}")
    print(f"  trials  = {trials} per (task, agent) cell")
    harbor_agent_evals(
        tasks=tasks, dataset=dataset, agents=agents, trials_per_cell=trials
    )
    show_results()
    print(
        "\nTip: run the same command again — completed shards cache-hit "
        "and only failed or new shards execute."
    )
