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
"""ZenML pipeline that runs a matrix of Harbor trials via the Sandbox bridge.

ZenML owns the outer orchestration (matrix expansion, per-trial steps,
retries, aggregation); Harbor keeps the trial eval kernel (task loading,
agent loop, verifier, reward). Each mapped step runs exactly one trial.

Invocation::

    python run.py [task] [agent_name] [n_trials]   # default: tasks/hello, oracle, 3

``task`` is a local task directory (``tasks/hello``) or a Harbor registry
dataset (``dataset:terminal-bench-sample@2.0``), which expands into one
trial per benchmark task::

    python run.py dataset:terminal-bench@2.0 oracle 1   # the full 89-task benchmark
"""

import asyncio
import io
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Annotated, Any, Tuple

from harbor.job import Job
from harbor.models.job.config import DatasetConfig, JobConfig
from harbor.models.job.result import JobResult
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    VerifierConfig,
)

from zenml import pipeline, step
from zenml.logger import get_logger
from zenml.types import MarkdownString

logger = get_logger(__name__)

# Import path Harbor uses to load our bridge — the env-side equivalent
# of ``--environment-import-path`` on the CLI.
_BRIDGE_IMPORT_PATH = "zenml_harbor_env:ZenMLSandboxEnvironment"

# Default task: writes "42" to /app/answer.txt, verifier scores 1.0
# iff the file matches. Hermetic — runs under the oracle agent so no
# LLM keys are required for the smoke test.
_DEFAULT_TASK_PATH = "tasks/hello"
_DEFAULT_AGENT = "oracle"

# Task spec prefixes accepted alongside plain local paths.
# ``dataset:NAME@VERSION`` names a Harbor registry dataset and expands —
# via Harbor's own resolver, so the task set and commit pins match
# ``harbor run`` exactly — into one ``git+URL@COMMIT:SUBPATH`` ref per
# task. Refs stay plain strings so the mapped trial steps fetch only
# their own pinned task at runtime, nothing ships with the example.
_DATASET_PREFIX = "dataset:"
_GIT_TASK_PREFIX = "git+"


def _expand_dataset(spec: str) -> list[str]:
    """Resolve a ``dataset:NAME@VERSION`` spec into git-pinned task refs.

    Args:
        spec: Dataset spec, e.g. ``dataset:terminal-bench@2.0``. The
            version is optional (``dataset:terminal-bench`` resolves the
            registry default).

    Returns:
        One ``git+URL@COMMIT:SUBPATH`` ref per task in the dataset.

    Raises:
        ValueError: If the dataset resolves to no tasks.
    """
    name, _, version = spec[len(_DATASET_PREFIX) :].partition("@")
    dataset = DatasetConfig(name=name, version=version or None)
    task_configs = asyncio.run(
        dataset.get_task_configs(disable_verification=True)
    )
    refs = []
    for tc in task_configs:
        if tc.git_url:
            pin = tc.git_commit_id or tc.ref or ""
            refs.append(f"{_GIT_TASK_PREFIX}{tc.git_url}@{pin}:{tc.path}")
        elif tc.path:
            refs.append(str(tc.path))
    if not refs:
        raise ValueError(f"Dataset spec {spec!r} resolved to no tasks.")
    return refs


def _task_config(task_ref: str) -> TaskConfig:
    """Build the single-trial TaskConfig for a local path or git ref.

    Args:
        task_ref: Local task directory (relative to this example) or a
            ``git+URL@COMMIT:SUBPATH`` ref from ``_expand_dataset``.

    Returns:
        A TaskConfig Harbor can resolve in this execution environment —
        git-backed refs are fetched by Harbor itself at trial start.

    Raises:
        FileNotFoundError: If a local ``task_ref`` does not resolve to
            an existing Harbor task directory.
    """
    if task_ref.startswith(_GIT_TASK_PREFIX):
        url, _, pinned = task_ref[len(_GIT_TASK_PREFIX) :].rpartition("@")
        pin, _, subpath = pinned.partition(":")
        return TaskConfig(
            git_url=url, git_commit_id=pin or None, path=Path(subpath)
        )
    here = Path(__file__).parent.resolve()
    task = (here / task_ref).resolve()
    if not task.exists():
        raise FileNotFoundError(f"Harbor task path not found: {task}")
    return TaskConfig(path=task)


def _display_name(task_ref: str) -> str:
    """Short task label for trial summaries and report rows."""
    if task_ref.startswith(_GIT_TASK_PREFIX):
        return Path(task_ref.rpartition(":")[-1]).name
    return task_ref


async def _run_harbor_job(
    task: TaskConfig,
    agent_name: str,
    jobs_dir: Path,
) -> dict[str, Any]:
    """Build a single-trial ``JobConfig`` and execute it via the bridge."""
    config = JobConfig(
        jobs_dir=jobs_dir,
        n_concurrent_trials=1,
        quiet=True,
        tasks=[task],
        agents=[AgentConfig(name=agent_name)],
        environment=EnvironmentConfig(import_path=_BRIDGE_IMPORT_PATH),
        verifier=VerifierConfig(),
    )

    job = await Job.create(config)
    result = await job.run()

    return {
        "job_id": str(result.id),
        "n_total": result.n_total_trials,
        "n_completed": result.stats.n_completed_trials,
        "n_errored": result.stats.n_errored_trials,
        "mean_reward": _mean_reward(result),
    }


def _mean_reward(result: JobResult) -> float | None:
    """Pull a single mean-reward scalar out of ``JobResult.stats.evals``.

    Harbor's stats nest one ``mean`` per eval bucket
    (``agent__dataset``). A single-trial job has one bucket, so we
    flatten by averaging across them — keeps the artifact's schema flat
    for the dashboard's metadata table.
    """
    means = [
        float(m["mean"])
        for stats in result.stats.evals.values()
        for m in stats.metrics
        if m.get("mean") is not None
    ]
    return sum(means) / len(means) if means else None


@step
def build_matrix(
    task_paths: list[str],
    agent_names: list[str],
    n_trials: int,
) -> Tuple[
    Annotated[list[str], "matrix_tasks"],
    Annotated[list[str], "matrix_agents"],
    Annotated[list[int], "matrix_trial_indices"],
]:
    """Expand a trial campaign into aligned per-trial parameter lists.

    Args:
        task_paths: Harbor tasks to evaluate — local task directories
            and/or ``dataset:NAME@VERSION`` registry specs, each of
            which expands to every task in the dataset.
        agent_names: Harbor agents to evaluate each task with.
        n_trials: Trials per (task, agent) combination.

    Returns:
        Three aligned lists (task, agent, trial index), one entry per
        trial, ready for ``run_harbor_trial.map``.
    """
    tasks, agents, indices = [], [], []
    for entry in task_paths:
        if entry.startswith(_DATASET_PREFIX):
            refs = _expand_dataset(entry)
            logger.info("%s expanded to %d task(s)", entry, len(refs))
        else:
            refs = [entry]
        for task in refs:
            for agent in agent_names:
                for index in range(n_trials):
                    tasks.append(task)
                    agents.append(agent)
                    indices.append(index)
    return tasks, agents, indices


@step
def run_harbor_trial(
    task_path: str,
    agent_name: str,
    trial_index: int = 0,
) -> Tuple[
    Annotated[dict[str, Any], "harbor_trial_result"],
    Annotated[bytes, "harbor_trial_artifacts"],
]:
    """Run one Harbor trial through the ZenML Sandbox bridge.

    Args:
        task_path: Filesystem path to the Harbor task, relative to
            this example's directory, or a ``git+URL@COMMIT:SUBPATH``
            ref produced by ``build_matrix`` from a dataset spec
            (Harbor fetches the pinned task itself at trial start).
        agent_name: One of Harbor's built-in agents (``oracle``,
            ``nop``, ``claude-code-agent``, ...).
        trial_index: Position of this trial within its (task, agent)
            campaign cell — recorded in the result for aggregation.

    Returns:
        Job summary (id, completion counts, mean reward) and a gzipped
        tarball of Harbor's ``jobs/`` tree (agent/verifier logs,
        trajectory).

    Raises:
        FileNotFoundError: If a local ``task_path`` does not resolve to
            an existing Harbor task directory.
    """
    task = _task_config(task_path)

    # ``asyncio.run`` is safe because ZenML steps run synchronously
    # today; revisit if step bodies grow an outer event loop.
    with tempfile.TemporaryDirectory(prefix="zenml-harbor-") as tmp:
        jobs_dir = Path(tmp)
        summary = asyncio.run(_run_harbor_job(task, agent_name, jobs_dir))
        summary["task"] = _display_name(task_path)
        summary["agent"] = agent_name
        summary["trial_index"] = trial_index
        # Harbor's ``jobs/`` tree is the only copy of the agent/verifier
        # logs and trajectory; tar it into the artifact store before the
        # tempdir vanishes.
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
            tf.add(jobs_dir, arcname=".")
        return summary, buffer.getvalue()


@step
def build_report(
    results: list[dict[str, Any]],
) -> Annotated[MarkdownString, "harbor_report"]:
    """Aggregate per-trial results into a campaign report.

    Args:
        results: Per-trial summaries from the fanned-out trial steps.

    Returns:
        A markdown report with per-(task, agent) trial counts and
        mean rewards.
    """
    cells: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in results:
        cells.setdefault((r["task"], r["agent"]), []).append(r)

    lines = [
        "# Harbor campaign report",
        "",
        f"{len(results)} trial(s) across {len(cells)} (task, agent) cell(s).",
        "",
        "| Task | Agent | Trials | Completed | Errored | Mean reward |",
        "|---|---|---|---|---|---|",
    ]
    for (task, agent), rs in sorted(cells.items()):
        rewards = [
            r["mean_reward"] for r in rs if r["mean_reward"] is not None
        ]
        mean = f"{sum(rewards) / len(rewards):.3f}" if rewards else "n/a"
        lines.append(
            f"| {task} | {agent} | {len(rs)} | "
            f"{sum(r['n_completed'] for r in rs)} | "
            f"{sum(r['n_errored'] for r in rs)} | {mean} |"
        )
    return MarkdownString("\n".join(lines))


@pipeline(dynamic=True, enable_cache=False)
def sandbox_harbor_pipeline(
    task_path: str = _DEFAULT_TASK_PATH,
    agent_name: str = _DEFAULT_AGENT,
    n_trials: int = 3,
) -> None:
    """Matrix fan-out: one Harbor trial per mapped ZenML step.

    ZenML expands the campaign matrix, runs each trial as its own step
    (own sandbox session, logs, retries, cache entry), and aggregates
    into a report; Harbor executes the single trial inside each step.
    """
    tasks, agents, indices = build_matrix(
        task_paths=[task_path], agent_names=[agent_name], n_trials=n_trials
    )
    results, _artifacts = run_harbor_trial.map(
        task_path=tasks, agent_name=agents, trial_index=indices
    ).unpack()
    build_report(results=results)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TASK_PATH
    agent = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_AGENT
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    print(
        "Running ZenML pipeline (Harbor campaign on the active stack's sandbox) ..."
    )
    print(f"  task   = {task}")
    print(f"  agent  = {agent}")
    print(f"  trials = {trials}")
    sandbox_harbor_pipeline(task_path=task, agent_name=agent, n_trials=trials)
    print("Done. Check the ZenML dashboard for the run + report.")
