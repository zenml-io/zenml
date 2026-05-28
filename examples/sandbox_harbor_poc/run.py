"""ZenML pipeline that runs a Harbor evaluation trial.

This is the single entry point for running Harbor evals on top of the
ZenML Sandbox component. The pipeline owns the run; its single step
builds a Harbor ``JobConfig`` pointed at the ``ZenMLSandboxEnvironment``
bridge, and ``Job.create(config).run()`` executes the trial inside
whatever Sandbox the active stack provides (Modal today; GKE Agent
Sandbox / Agent Substrate later).

Everything Harbor produces — reward, ATIF, agent/verifier logs, exit
codes — comes back as ``JobResult`` and lands as a ZenML artifact
attached to the pipeline run, so you get full lineage, caching, and
the dashboard view by default.

Invocation::

    python run.py                            # default: tasks/hello, oracle
    python run.py tasks/hello oracle
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path
from typing import Annotated, Any

from harbor.job import Job
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    VerifierConfig,
)

from zenml import pipeline, step
from zenml.logger import get_logger

logger = get_logger(__name__)

# Import path Harbor uses to load our bridge — the env-side equivalent
# of ``--environment-import-path`` on the CLI.
_BRIDGE_IMPORT_PATH = "zenml_sandbox_env:ZenMLSandboxEnvironment"

# Default task: writes "42" to /app/answer.txt, verifier scores 1.0
# iff the file matches. Hermetic — runs under the oracle agent so no
# LLM keys are required for the smoke test.
_DEFAULT_TASK_PATH = "tasks/hello"
_DEFAULT_AGENT = "oracle"


async def _run_harbor_job(
    task_path: Path,
    agent_name: str,
    jobs_dir: Path,
) -> dict[str, Any]:
    """Build a single-trial ``JobConfig`` and execute it via the bridge."""
    config = JobConfig(
        jobs_dir=jobs_dir,
        n_concurrent_trials=1,
        quiet=True,
        tasks=[TaskConfig(path=task_path)],
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


def _mean_reward(result: Any) -> float | None:
    """Pull a single mean-reward scalar out of ``JobResult.stats.evals``.

    Harbor's stats nest one ``mean`` per eval bucket
    (``agent__dataset``). A POC job has a single bucket, so we flatten
    by averaging across them — keeps the artifact's schema flat for
    the dashboard's metadata table.
    """
    evals = result.stats.evals or {}
    means: list[float] = []
    for eval_stats in evals.values():
        for metric in eval_stats.metrics or []:
            mean = metric.get("mean") if isinstance(metric, dict) else None
            if mean is not None:
                means.append(float(mean))
    if not means:
        return None
    return sum(means) / len(means)


@step
def run_harbor_trial(
    task_path: str = _DEFAULT_TASK_PATH,
    agent_name: str = _DEFAULT_AGENT,
) -> Annotated[dict[str, Any], "harbor_trial_result"]:
    """Run one Harbor trial through the ZenML Sandbox bridge.

    Args:
        task_path: Filesystem path to the Harbor task, relative to
            this example's directory.
        agent_name: One of Harbor's built-in agents (``oracle``,
            ``nop``, ``claude-code-agent``, ...).

    Returns:
        Job id, completion counts, mean reward across trials.
    """
    here = Path(__file__).parent.resolve()
    task = (here / task_path).resolve()
    if not task.exists():
        raise FileNotFoundError(f"Harbor task path not found: {task}")

    # Per-step jobs dir; we throw the on-disk trace away and trust
    # the ZenML artifact as the durable record of the trial.
    jobs_dir = here / ".zenml_harbor_jobs"
    if jobs_dir.exists():
        shutil.rmtree(jobs_dir)
    jobs_dir.mkdir()

    try:
        return asyncio.run(_run_harbor_job(task, agent_name, jobs_dir))
    finally:
        logger.info("Harbor on-disk trace at %s", jobs_dir)


@pipeline(enable_cache=False)
def sandbox_harbor_poc_pipeline(
    task_path: str = _DEFAULT_TASK_PATH,
    agent_name: str = _DEFAULT_AGENT,
) -> dict[str, Any]:
    """Single-step pipeline: ZenML on top, Harbor running inside."""
    return run_harbor_trial(task_path=task_path, agent_name=agent_name)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TASK_PATH
    agent = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_AGENT
    print("Running ZenML pipeline (Harbor on Modal sandbox) ...")
    print(f"  task  = {task}")
    print(f"  agent = {agent}")
    sandbox_harbor_poc_pipeline(task_path=task, agent_name=agent)
    print("Done. Check the ZenML dashboard for the run + artifact.")
