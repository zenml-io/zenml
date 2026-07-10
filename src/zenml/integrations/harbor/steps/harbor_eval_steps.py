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
"""Reusable steps for running Harbor eval campaigns as ZenML pipelines.

A minimal campaign pipeline composes the three steps like this::

    from zenml import pipeline
    from zenml.integrations.harbor.steps import (
        build_harbor_matrix,
        build_harbor_report,
        run_harbor_shard,
    )

    @pipeline(dynamic=True)
    def harbor_eval_pipeline(
        tasks: list[str], agents: list[dict], trials_per_cell: int = 1
    ) -> None:
        shards = build_harbor_matrix(
            tasks=tasks, agents=agents, trials_per_cell=trials_per_cell
        )
        results = run_harbor_shard.map(shard=shards)
        build_harbor_report(results=results)
"""

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple

from zenml import log_metadata, save_artifact, step
from zenml.integrations.harbor.job_runner import (
    resolve_dataset,
    run_shard_job,
)
from zenml.integrations.harbor.materializers import (
    HarborShardResultMaterializer,
)
from zenml.integrations.harbor.models import (
    HarborShardResult,
    HarborShardSpec,
    TaskRef,
)
from zenml.integrations.harbor.utils import pack_shards
from zenml.logger import get_logger
from zenml.types import MarkdownString

logger = get_logger(__name__)


@step
def build_harbor_matrix(
    tasks: Optional[List[str]] = None,
    dataset: Optional[Dict[str, Any]] = None,
    agents: Optional[List[Dict[str, Any]]] = None,
    trials_per_cell: int = 1,
    trials_per_step: int = 1,
) -> Annotated[List[Dict[str, Any]], "harbor_shards"]:
    """Expand a Harbor eval campaign into mapped-step shards.

    Args:
        tasks: Task specs — local task directories and/or pinned
            ``git+URL@COMMIT:SUBPATH`` refs. Local paths must be visible
            to every shard step, so use git/dataset tasks for remote
            orchestrators.
        dataset: Keyword arguments for Harbor's ``DatasetConfig`` (e.g.
            ``{"name": "terminal-bench", "version": "2.0"}``), expanded
            via Harbor's own resolver into git-pinned per-task refs.
        agents: Agent specifications, each a dict with ``name`` and
            optionally ``model_name``, ``kwargs`` and ``env``. Defaults
            to Harbor's hermetic ``oracle`` agent.
        trials_per_cell: Trials per (task, agent) combination.
        trials_per_step: Maximum trials per shard. Each shard runs as
            one mapped step (one Harbor job) with its own retry and
            cache granularity.

    Returns:
        JSON-serializable shard specifications, one per mapped step.

    Raises:
        ValueError: If the campaign contains no tasks.
        FileNotFoundError: If a local task path does not exist.
    """
    task_refs = []
    for spec in tasks or []:
        task_ref = TaskRef.parse(spec)
        if task_ref.path and not task_ref.git_url:
            local_path = Path(task_ref.path).resolve()
            if not local_path.exists():
                raise FileNotFoundError(
                    f"Harbor task path not found: {local_path}"
                )
            task_ref.path = str(local_path)
        task_refs.append(task_ref)
    if dataset:
        resolved = resolve_dataset(dataset)
        logger.info(
            "Dataset %s expanded to %d task(s).", dataset, len(resolved)
        )
        task_refs.extend(resolved)
    if not task_refs:
        raise ValueError(
            "The campaign contains no tasks. Provide `tasks` and/or a "
            "`dataset`."
        )

    shards = pack_shards(
        tasks=task_refs,
        agents=agents or [{"name": "oracle"}],
        trials_per_cell=trials_per_cell,
        trials_per_step=trials_per_step,
    )
    logger.info(
        "Campaign expanded to %d shard(s) across %d task(s).",
        len(shards),
        len(task_refs),
    )
    return [shard.model_dump(mode="json") for shard in shards]


# The materializer is pinned explicitly instead of relying on
# `HarborIntegration.activate()`: activation is skipped whenever
# `check_installation()` finds any transitive requirement out of range,
# which would silently fall back to PydanticMaterializer and drop the
# job archive.
@step(output_materializers=HarborShardResultMaterializer)
def run_harbor_shard(
    shard: Dict[str, Any],
    n_concurrent_trials: int = 4,
    timeout_multiplier: float = 1.0,
    harbor_retry_max: int = 0,
    fail_on_trial_error: bool = False,
) -> Annotated[HarborShardResult, "harbor_shard_result"]:
    """Run one campaign shard as a single Harbor job.

    Step-level caching is deliberately left enabled: on an identical
    campaign rerun, shards that already completed are cache hits and
    only previously failed or new shards execute. Combine with
    ``@step(retry=...)`` via ``with_options`` for flaky-infrastructure
    resilience.

    Every shard logs ``harbor.error_rate`` (errored / total trials).
    ``harbor.mean_reward`` averages the scored trials only, so a
    reward-threshold gate must be paired with an error-rate gate to
    catch shards whose signal was destroyed by trial errors; a shard
    whose trials all errored *without producing any score* additionally
    logs ``harbor.mean_reward = 0.0`` so pure reward gates fail safe on
    a fully crashed campaign. Trials that scored before erroring keep
    their real mean — the error-rate gate is what flags those. A shard
    that finished without errors but was never scored (the verifier
    returned no rewards) logs no ``harbor.mean_reward`` at all — that
    is absence of signal, not a zero score.

    Args:
        shard: A shard specification produced by ``build_harbor_matrix``.
        n_concurrent_trials: Upper bound on trials Harbor runs
            concurrently inside this shard.
        timeout_multiplier: Multiplier applied to all task timeouts.
        harbor_retry_max: Max Harbor-internal retries per errored trial.
        fail_on_trial_error: If True, fail the step when any trial in
            the shard errored (exception during execution, not a low
            reward). A failed step has no cache entry, so a rerun
            re-executes exactly these shards. Off by default because an
            agent failing a task is a result, not an error.

    Returns:
        The shard result. Harbor's full job directory (agent/verifier
        logs, trajectories) is archived alongside it in the artifact
        store.

    Raises:
        RuntimeError: If ``fail_on_trial_error`` is set and at least one
            trial errored.
    """
    spec = HarborShardSpec.model_validate(shard)
    # Not a context manager: the materializer archives the job dir
    # after the step function returns. The directory is left behind on
    # local orchestrators (it lives under the system temp dir).
    jobs_dir = Path(tempfile.mkdtemp(prefix="zenml-harbor-"))
    result = run_shard_job(
        spec=spec,
        jobs_dir=jobs_dir,
        n_concurrent_trials=n_concurrent_trials,
        timeout_multiplier=timeout_multiplier,
        harbor_retry_max=harbor_retry_max,
    )

    metadata: Dict[str, Any] = {
        "harbor.shard_id": spec.shard_id,
        "harbor.task": spec.task.display_name,
        "harbor.agent": spec.agent_name,
        "harbor.n_trials": len(spec.trial_indices),
        "harbor.n_succeeded": result.n_succeeded,
        "harbor.n_errored": result.n_errored,
        "harbor.error_rate": result.error_rate,
    }
    if spec.model_name:
        metadata["harbor.model"] = spec.model_name
    mean_reward = result.mean_reward
    if mean_reward is not None:
        if len(mean_reward) == 1:
            metadata["harbor.mean_reward"] = next(iter(mean_reward.values()))
        else:
            metadata["harbor.mean_rewards"] = mean_reward
    elif (
        result.n_total_trials > 0 and result.n_errored == result.n_total_trials
    ):
        # All trials errored and none scored: log an explicit 0.0 so
        # reward-threshold gates fail safe (the docstring has the full
        # sentinel rule).
        metadata["harbor.mean_reward"] = 0.0
    cost = result.total_cost_usd
    if cost is not None:
        metadata["harbor.cost_usd"] = cost
    # Step-run metadata is the queryable surface, e.g.
    # client.list_run_steps(run_metadata=["harbor.mean_reward:lt:1"]).
    log_metadata(metadata=metadata)

    if fail_on_trial_error and result.n_errored > 0:
        # Failing the step means the materializer never runs, which
        # would lose the job archive — the logs a user needs to debug
        # exactly these errored trials. Rescue it as a manual artifact
        # before raising.
        rescue_name = f"harbor_shard_result_{spec.shard_id[:12]}_failed"
        save_artifact(
            result,
            name=rescue_name,
            materializer=HarborShardResultMaterializer,
        )
        raise RuntimeError(
            f"{result.n_errored} of {result.n_total_trials} trial(s) in "
            f"shard {spec.shard_id[:12]} errored. The shard result and "
            f"Harbor job archive were saved as artifact '{rescue_name}'."
        )
    return result


@step
def build_harbor_report(
    results: List[HarborShardResult],
) -> Annotated[MarkdownString, "harbor_report"]:
    """Aggregate shard results into a campaign report.

    Args:
        results: The shard results of the campaign.

    Returns:
        A Markdown report with one row per (task, agent, model) cell
        plus campaign totals.
    """
    cells: Dict[Tuple[str, str, str], List[HarborShardResult]] = {}
    for result in results:
        # Same-named agents with different kwargs/env are distinct
        # experiments — suffix a config digest so they get separate rows.
        agent_label = result.spec.agent_name
        if result.spec.agent_kwargs or result.spec.agent_env:
            config_digest = hashlib.sha256(
                json.dumps(
                    {
                        "kwargs": result.spec.agent_kwargs,
                        "env": result.spec.agent_env,
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()[:6]
            agent_label = f"{agent_label} (cfg {config_digest})"
        key = (
            result.spec.task.display_name,
            agent_label,
            result.spec.model_name or "",
        )
        cells.setdefault(key, []).append(result)

    n_trials = sum(r.n_total_trials for r in results)
    lines = [
        "# Harbor campaign report",
        "",
        f"{n_trials} trial(s) in {len(results)} shard(s) across "
        f"{len(cells)} (task, agent, model) cell(s).",
        "",
        "| Task | Agent | Model | Trials | Succeeded | Errored | "
        "Mean reward | Cost (USD) |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def _format_cell(shards: List[HarborShardResult]) -> Tuple[str, str]:
        sums: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for shard in shards:
            for trial in shard.trials:
                for key, value in (trial.rewards or {}).items():
                    sums[key] = sums.get(key, 0.0) + value
                    counts[key] = counts.get(key, 0) + 1
        rewards = (
            ", ".join(f"{key}={sums[key] / counts[key]:.3f}" for key in sums)
            if counts
            else "n/a"
        )
        costs = [
            shard.total_cost_usd
            for shard in shards
            if shard.total_cost_usd is not None
        ]
        cost = f"{sum(costs):.4f}" if costs else "n/a"
        return rewards, cost

    total_succeeded = 0
    total_errored = 0
    for (task, agent, model), shards in sorted(cells.items()):
        succeeded = sum(s.n_succeeded for s in shards)
        errored = sum(s.n_errored for s in shards)
        total_succeeded += succeeded
        total_errored += errored
        rewards, cost = _format_cell(shards)
        lines.append(
            f"| {task} | {agent} | {model or 'n/a'} | "
            f"{sum(s.n_total_trials for s in shards)} | {succeeded} | "
            f"{errored} | {rewards} | {cost} |"
        )
    rewards, cost = _format_cell(results)
    lines.append(
        f"| **Total** | | | {n_trials} | {total_succeeded} | "
        f"{total_errored} | {rewards} | {cost} |"
    )
    return MarkdownString("\n".join(lines))
