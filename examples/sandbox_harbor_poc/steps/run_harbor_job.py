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
"""Step: run one Harbor trial (one task) through the ZenML Sandbox bridge.

The campaign maps this step across the ``agent x model x task`` matrix, so
each invocation evaluates a single task and runs in its own Sandbox. It
never shells out to ``harbor run`` and never touches an external env
provider (Docker / Daytona): it builds a Harbor ``JobConfig`` in process
and executes it via ``Job.create(config).run()``, pointing Harbor's
environment at the ``ZenMLSandboxEnvironment`` bridge. The trial therefore
runs inside whatever Sandbox the active ZenML stack provides, and the
on-disk job tree is returned as a ZenML artifact for full lineage.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Annotated

from harbor.job import Job
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    VerifierConfig,
)
from models.harbor_models import HarborRunSpec

from zenml import log_metadata, step

logger = logging.getLogger(__name__)

# Import path Harbor uses to load our bridge — the env-side equivalent
# of ``--environment-import-path`` on the CLI. Mirrors run.py.
_BRIDGE_IMPORT_PATH = "zenml_sandbox_env:ZenMLSandboxEnvironment"


def _resolve_task_path(task_path: str) -> Path:
    """Resolve a single task directory to an absolute path.

    Local orchestrators run relative to the example directory; on
    Kubernetes the code is mounted under /app/ or /app/code/. We probe
    the same candidate roots build_matrix uses so the step works in
    both places.

    Args:
        task_path: Task directory from the run spec, absolute or relative.

    Returns:
        The first existing candidate as an absolute path.

    Raises:
        FileNotFoundError: If no candidate directory exists.
    """
    p = Path(task_path)
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        Path(__file__).parent.parent / task_path,
        Path("/app") / task_path,
        Path("/app/code") / task_path,
        p,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(
        f"Task path not found. Tried: {[str(c) for c in candidates]}"
    )


def _build_agent_config(spec: HarborRunSpec) -> AgentConfig:
    """Build the AgentConfig, attaching the LLM model when the spec sets one.

    Harbor's ``AgentConfig`` carries the LLM via ``model_name`` (the
    programmatic equivalent of the CLI's ``-m`` flag). The oracle agent
    needs no model, so we only set ``model_name`` when the spec provides
    one — keeping the oracle path identical to ``AgentConfig(name=...)``.

    Args:
        spec: The Harbor run specification.

    Returns:
        An AgentConfig for the spec's agent.
    """
    if spec.model:
        return AgentConfig(name=spec.agent, model_name=spec.model)
    return AgentConfig(name=spec.agent)


async def _run_harbor_job(spec: HarborRunSpec, jobs_dir: Path) -> Path:
    """Build a single-task JobConfig and execute it via the Sandbox bridge.

    Args:
        spec: The Harbor run specification (one agent/model/task).
        jobs_dir: Persistent directory Harbor writes its job tree into.

    Returns:
        Path to the Harbor job output directory.
    """
    task_path = _resolve_task_path(spec.task_path)

    config = JobConfig(
        jobs_dir=jobs_dir,
        n_concurrent_trials=1,
        quiet=True,
        tasks=[TaskConfig(path=str(task_path))],
        agents=[_build_agent_config(spec)],
        environment=EnvironmentConfig(import_path=_BRIDGE_IMPORT_PATH),
        verifier=VerifierConfig(),
    )

    job = await Job.create(config)
    result = await job.run()
    logger.info(
        "Harbor job %s finished: %d trial(s) for %s",
        result.id,
        result.n_total_trials,
        spec.label,
    )
    return _find_job_dir(jobs_dir)


def _find_job_dir(jobs_dir: Path) -> Path:
    """Locate the Harbor job directory under ``jobs_dir``.

    Harbor writes a job into a timestamped directory. Depending on the
    Harbor version that lands either directly under ``jobs_dir``
    (``<jobs_dir>/<timestamp>/``) or nested under a ``jobs/`` subdir, so
    we probe both and pick the newest directory by mtime.

    Args:
        jobs_dir: The directory handed to ``JobConfig.jobs_dir``.

    Returns:
        Path to the most recent job directory.

    Raises:
        FileNotFoundError: If Harbor produced no job directory.
    """
    for root in (jobs_dir / "jobs", jobs_dir):
        if not root.is_dir():
            continue
        job_dirs = [d for d in root.iterdir() if d.is_dir()]
        if job_dirs:
            return max(job_dirs, key=lambda d: d.stat().st_mtime)
    raise FileNotFoundError(
        f"No Harbor job directory found under {jobs_dir}. "
        f"Harbor may not have run successfully."
    )


@step(enable_cache=False)
def run_harbor_job(spec: HarborRunSpec) -> Annotated[Path, "job_dir"]:
    """Run one Harbor trial (one task) through the Sandbox bridge.

    Builds a single-task Harbor ``JobConfig`` whose environment is the
    ``ZenMLSandboxEnvironment`` bridge and executes it programmatically,
    so the trial runs inside the active stack's Sandbox component rather
    than a Harbor env provider. ``spec.env_provider`` is intentionally
    ignored on this path (see HarborRunSpec).

    Args:
        spec: The Harbor run specification (one agent/model/task).

    Returns:
        Path to the Harbor job output directory. The built-in
        PathMaterializer archives the whole tree as a versioned .tar.gz
        artifact, so the agent/verifier logs and rewards are preserved
        with full lineage.
    """
    # Surface which LLM keys are visible — non-oracle agents need them
    # inside the Sandbox; the oracle agent needs none.
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(k)
        logger.info(
            "ENV %s = %s", k, f"set ({len(val)} chars)" if val else "NOT SET"
        )

    # jobs_dir MUST outlive the step: ZenML's PathMaterializer archives it
    # AFTER the step returns. A TemporaryDirectory context would delete the
    # tree on exit, so we use mkdtemp and leave cleanup to the OS / artifact
    # store. asyncio.run is safe because ZenML steps run synchronously.
    jobs_dir = Path(tempfile.mkdtemp(prefix="harbor_"))
    logger.info(
        "Running Harbor job for %s (jobs_dir=%s)", spec.label, jobs_dir
    )

    job_dir = asyncio.run(_run_harbor_job(spec, jobs_dir))
    logger.info("Found job directory: %s", job_dir)

    log_metadata(
        metadata={
            "agent": spec.agent,
            "model": spec.model or "none",
            "task": spec.task_name,
            "label": spec.label,
            "job_dir_name": job_dir.name,
        }
    )

    return job_dir
