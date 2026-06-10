"""ZenML pipeline that runs a Harbor evaluation trial via the Sandbox bridge.

Invocation::

    python run.py [task_path] [agent_name]   # default: tasks/hello, oracle
"""

from __future__ import annotations

import asyncio
import io
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Annotated, Any, Tuple

from harbor.job import Job
from harbor.models.job.config import JobConfig
from harbor.models.job.result import JobResult
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


def _mean_reward(result: JobResult) -> float | None:
    """Pull a single mean-reward scalar out of ``JobResult.stats.evals``.

    Harbor's stats nest one ``mean`` per eval bucket
    (``agent__dataset``). A POC job has a single bucket, so we flatten
    by averaging across them — keeps the artifact's schema flat for
    the dashboard's metadata table.
    """
    means = [
        float(m["mean"])
        for stats in result.stats.evals.values()
        for m in stats.metrics
        if m.get("mean") is not None
    ]
    return sum(means) / len(means) if means else None


@step
def run_harbor_trial(
    task_path: str,
    agent_name: str,
) -> Tuple[
    Annotated[dict[str, Any], "harbor_trial_result"],
    Annotated[bytes, "harbor_trial_artifacts"],
]:
    """Run one Harbor trial through the ZenML Sandbox bridge.

    Args:
        task_path: Filesystem path to the Harbor task, relative to
            this example's directory.
        agent_name: One of Harbor's built-in agents (``oracle``,
            ``nop``, ``claude-code-agent``, ...).

    Returns:
        Job summary (id, completion counts, mean reward) and a gzipped
        tarball of Harbor's ``jobs/`` tree (agent/verifier logs,
        trajectory).

    Raises:
        FileNotFoundError: If ``task_path`` does not resolve to an
            existing Harbor task directory.
    """
    here = Path(__file__).parent.resolve()
    task = (here / task_path).resolve()
    if not task.exists():
        raise FileNotFoundError(f"Harbor task path not found: {task}")

    # ``asyncio.run`` is safe because ZenML steps run synchronously
    # today; revisit if step bodies grow an outer event loop.
    with tempfile.TemporaryDirectory(prefix="zenml-harbor-") as tmp:
        jobs_dir = Path(tmp)
        summary = asyncio.run(_run_harbor_job(task, agent_name, jobs_dir))
        # Harbor's ``jobs/`` tree is the only copy of the agent/verifier
        # logs and trajectory; tar it into the artifact store before the
        # tempdir vanishes.
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
            tf.add(jobs_dir, arcname=".")
        return summary, buffer.getvalue()


@pipeline(enable_cache=False)
def sandbox_harbor_poc_pipeline(
    task_path: str = _DEFAULT_TASK_PATH,
    agent_name: str = _DEFAULT_AGENT,
) -> None:
    """Single-step pipeline: ZenML on top, Harbor running inside."""
    run_harbor_trial(task_path=task_path, agent_name=agent_name)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TASK_PATH
    agent = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_AGENT
    print("Running ZenML pipeline (Harbor on the active stack's sandbox) ...")
    print(f"  task  = {task}")
    print(f"  agent = {agent}")
    sandbox_harbor_poc_pipeline(task_path=task, agent_name=agent)
    print("Done. Check the ZenML dashboard for the run + artifacts.")
